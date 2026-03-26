# -*- coding: utf-8 -*-
"""
plan_compiler.py

【Plan Compiler V1｜冻结版】

职责：
1. 读取 scene_plan.json
2. 读取 element_plan.json
3. 读取 timing_plan.json
4. 按 scene_id 合并为统一 compiled_plan
5. 输出 compiled_plan.json 与下游兼容文件

注意：
- 本模块只处理 SCENE + ELEMENT + TIMING → COMPILED_PLAN
- 不做素材匹配
- 不做音频对齐
- 不做动画编排
- 不改前面三层模块逻辑
"""

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DATA_CURRENT_DIR = BASE_DIR / "data" / "current"

ROOT_SCENE_PLAN_FILE = BASE_DIR / "scene_plan.json"
DATA_CURRENT_SCENE_PLAN_FILE = DATA_CURRENT_DIR / "scene_plan.json"
ROOT_ELEMENT_PLAN_FILE = BASE_DIR / "element_plan.json"
DATA_CURRENT_ELEMENT_PLAN_FILE = DATA_CURRENT_DIR / "element_plan.json"
ROOT_TIMING_PLAN_FILE = BASE_DIR / "timing_plan.json"
DATA_CURRENT_TIMING_PLAN_FILE = DATA_CURRENT_DIR / "timing_plan.json"
ROOT_COMPILED_PLAN_FILE = BASE_DIR / "compiled_plan.json"
DATA_CURRENT_COMPILED_PLAN_FILE = DATA_CURRENT_DIR / "compiled_plan.json"


def load_plan_file(root_file, current_file, plan_name):
    """优先读取根目录文件，不存在时读取 data/current 兼容文件。"""
    input_file = None

    if root_file.exists():
        input_file = root_file
    elif current_file.exists():
        input_file = current_file
    else:
        raise FileNotFoundError(f"{plan_name} 不存在：{root_file} 或 {current_file}")

    with open(input_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, list):
        scenes = data
    elif isinstance(data, dict):
        scenes = data.get("scenes", [])
    else:
        scenes = []

    if not isinstance(scenes, list):
        scenes = []

    return scenes, input_file


def build_scene_map(scenes):
    """将 scenes 转为便于按 scene_id 优先合并的映射结构。"""
    scene_map = {}
    ordered_keys = []

    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            scene = {}

        raw_scene_id = scene.get("scene_id")
        has_scene_id = raw_scene_id is not None and raw_scene_id != ""

        if has_scene_id:
            merge_key = f"id:{raw_scene_id}"
        else:
            merge_key = f"idx:{index}"

        scene_map[merge_key] = {
            "data": scene,
            "index": index,
            "scene_id": raw_scene_id if has_scene_id else index,
            "has_scene_id": has_scene_id,
        }
        ordered_keys.append(merge_key)

    return scene_map, ordered_keys


def _get_sorted_scene_keys(scene_map, ordered_keys):
    """按 scene_id 升序排序；若不可用，则按原顺序保底。"""
    def sort_key(merge_key):
        info = scene_map.get(merge_key, {})
        scene_id = info.get("scene_id")
        index = info.get("index", 0)

        try:
            numeric_scene_id = int(scene_id)
            return (0, numeric_scene_id, index)
        except (TypeError, ValueError):
            return (1, index, 0)

    return sorted(ordered_keys, key=sort_key)


def compile_plan(scene_scenes, element_scenes, timing_scenes):
    """按 scene_id 优先合并三层结构，并计算 total_duration。"""
    scene_map, scene_keys = build_scene_map(scene_scenes)
    element_map, element_keys = build_scene_map(element_scenes)
    timing_map, timing_keys = build_scene_map(timing_scenes)

    combined_map = {}
    combined_order = []

    for source_map, source_keys in (
        (scene_map, scene_keys),
        (element_map, element_keys),
        (timing_map, timing_keys),
    ):
        for key in source_keys:
            if key not in combined_map:
                combined_map[key] = source_map.get(key, {})
                combined_order.append(key)
            else:
                existing_info = combined_map[key]
                new_info = source_map.get(key, {})
                if not existing_info.get("has_scene_id") and new_info.get("has_scene_id"):
                    combined_map[key] = new_info

    sorted_keys = _get_sorted_scene_keys(combined_map, combined_order)
    compiled_plan = []
    total_duration = 0.0

    for index, key in enumerate(sorted_keys):
        scene_info = scene_map.get(key, {})
        element_info = element_map.get(key, {})
        timing_info = timing_map.get(key, {})

        scene_data = scene_info.get("data", {}) if isinstance(scene_info.get("data", {}), dict) else {}
        element_data = element_info.get("data", {}) if isinstance(element_info.get("data", {}), dict) else {}
        timing_data = timing_info.get("data", {}) if isinstance(timing_info.get("data", {}), dict) else {}

        scene_id = scene_data.get(
            "scene_id",
            element_data.get(
                "scene_id",
                timing_data.get("scene_id", index)
            )
        )
        role = str(scene_data.get("role", element_data.get("role", timing_data.get("role", ""))) or "")
        scene_type = str(scene_data.get("type", element_data.get("type", timing_data.get("type", ""))) or "")
        text = str(scene_data.get("text", element_data.get("text", timing_data.get("text", ""))) or "")

        elements = element_data.get("elements", [])
        if not isinstance(elements, list):
            elements = []

        duration = timing_data.get("duration", 0.0)
        start_time = timing_data.get("start_time", 0.0)
        end_time = timing_data.get("end_time", 0.0)

        try:
            duration = round(float(duration), 1)
        except (TypeError, ValueError):
            duration = 0.0

        try:
            start_time = round(float(start_time), 1)
        except (TypeError, ValueError):
            start_time = 0.0

        try:
            end_time = round(float(end_time), 1)
        except (TypeError, ValueError):
            end_time = 0.0

        compiled_scene = {
            "scene_id": scene_id,
            "role": role,
            "type": scene_type,
            "text": text,
            "elements": elements,
            "duration": duration,
            "start_time": start_time,
            "end_time": end_time,
        }

        # 透传 scene 层扩展字段：有则保留，无则不强行添加。
        for field_name in (
            "user_anchor",
            "user_local_assets",
            "visual_inserts",
            "segments",
            "expression_enhancements",
        ):
            if field_name in scene_data:
                compiled_scene[field_name] = scene_data[field_name]

        compiled_plan.append(compiled_scene)
        total_duration = max(total_duration, end_time)

    return compiled_plan, round(total_duration, 1)


def save_compiled_plan(compiled_plan, total_duration):
    """写入根目录与下游兼容的 compiled_plan.json。"""
    DATA_CURRENT_DIR.mkdir(parents=True, exist_ok=True)

    with open(ROOT_COMPILED_PLAN_FILE, "w", encoding="utf-8") as file:
        json.dump(compiled_plan, file, ensure_ascii=False, indent=2)

    downstream_output = {
        "scenes": compiled_plan,
        "total_duration": total_duration,
    }
    with open(DATA_CURRENT_COMPILED_PLAN_FILE, "w", encoding="utf-8") as file:
        json.dump(downstream_output, file, ensure_ascii=False, indent=2)


def main():
    print("=" * 60)
    print("开始生成 Plan Compiler V1...")
    print("=" * 60)

    scene_scenes, scene_file = load_plan_file(
        ROOT_SCENE_PLAN_FILE,
        DATA_CURRENT_SCENE_PLAN_FILE,
        "scene_plan.json",
    )
    print(f"已读取 scene_plan.json：{scene_file}")

    element_scenes, element_file = load_plan_file(
        ROOT_ELEMENT_PLAN_FILE,
        DATA_CURRENT_ELEMENT_PLAN_FILE,
        "element_plan.json",
    )
    print(f"已读取 element_plan.json：{element_file}")

    timing_scenes, timing_file = load_plan_file(
        ROOT_TIMING_PLAN_FILE,
        DATA_CURRENT_TIMING_PLAN_FILE,
        "timing_plan.json",
    )
    print(f"已读取 timing_plan.json：{timing_file}")

    compiled_plan, total_duration = compile_plan(scene_scenes, element_scenes, timing_scenes)
    save_compiled_plan(compiled_plan, total_duration)

    print(f"已生成 compiled_plan.json：{ROOT_COMPILED_PLAN_FILE}")
    print(f"已生成下游兼容 compiled_plan.json：{DATA_CURRENT_COMPILED_PLAN_FILE}")
    print(f"场景数量：{len(compiled_plan)}")
    print(f"总时长：{total_duration:.1f} 秒")
    print("=" * 60)


if __name__ == "__main__":
    main()
