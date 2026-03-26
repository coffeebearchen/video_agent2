# -*- coding: utf-8 -*-
"""
element_builder.py

【Element Builder V1｜冻结版】

职责：
1. 读取 scene_plan.json
2. 为每个 scene 补出固定元素结构
3. 输出 element_plan.json
4. 输出下游兼容的 data/current/element_plan.json

注意：
- 本模块只处理 SCENE → ELEMENTS
- 不做素材匹配
- 不做 timing
- 不做渲染与视频合成
"""

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
ROOT_SCENE_PLAN_FILE = BASE_DIR / "scene_plan.json"
DATA_CURRENT_SCENE_PLAN_FILE = BASE_DIR / "data" / "current" / "scene_plan.json"
ROOT_ELEMENT_PLAN_FILE = BASE_DIR / "element_plan.json"
DATA_CURRENT_DIR = BASE_DIR / "data" / "current"
DATA_CURRENT_ELEMENT_PLAN_FILE = DATA_CURRENT_DIR / "element_plan.json"


def load_scene_plan():
    """读取 scene_plan.json，兼容 list 与 {'scenes': [...]} 两种结构。"""
    input_file = None

    if ROOT_SCENE_PLAN_FILE.exists():
        input_file = ROOT_SCENE_PLAN_FILE
    elif DATA_CURRENT_SCENE_PLAN_FILE.exists():
        input_file = DATA_CURRENT_SCENE_PLAN_FILE
    else:
        raise FileNotFoundError(
            f"scene_plan.json 不存在：{ROOT_SCENE_PLAN_FILE} 或 {DATA_CURRENT_SCENE_PLAN_FILE}"
        )

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


def build_elements_for_scene(scene):
    """根据 scene type 生成固定的 elements 结构。"""
    scene_type = str(scene.get("type", "") or "").strip().lower()

    if scene_type == "overlay":
        return [
            {
                "element_type": "video",
                "purpose": "background"
            },
            {
                "element_type": "text",
                "purpose": "main_message"
            }
        ]

    if scene_type == "explain":
        return [
            {
                "element_type": "video",
                "purpose": "background"
            },
            {
                "element_type": "text",
                "purpose": "main_message"
            },
            {
                "element_type": "image_card",
                "purpose": "explanation_support"
            }
        ]

    if scene_type == "card":
        return [
            {
                "element_type": "text",
                "purpose": "summary"
            }
        ]

    return [
        {
            "element_type": "text",
            "purpose": "fallback"
        }
    ]


def build_element_plan(scenes):
    """遍历 scenes，生成完整的 element_plan 列表。"""
    element_plan = []

    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            scene = {}

        scene_id = scene.get("scene_id", index)
        role = str(scene.get("role", "") or "")
        scene_type = str(scene.get("type", "") or "")
        text = str(scene.get("text", "") or "")

        element_plan.append({
            "scene_id": scene_id,
            "role": role,
            "type": scene_type,
            "text": text,
            "elements": build_elements_for_scene(scene)
        })

    return element_plan


def save_element_plan(element_plan):
    """写入根目录与下游兼容的 element_plan.json。"""
    DATA_CURRENT_DIR.mkdir(parents=True, exist_ok=True)

    with open(ROOT_ELEMENT_PLAN_FILE, "w", encoding="utf-8") as file:
        json.dump(element_plan, file, ensure_ascii=False, indent=2)

    downstream_output = {
        "scenes": element_plan
    }
    with open(DATA_CURRENT_ELEMENT_PLAN_FILE, "w", encoding="utf-8") as file:
        json.dump(downstream_output, file, ensure_ascii=False, indent=2)


def main():
    print("=" * 60)
    print("开始生成 Element Builder V1...")
    print("=" * 60)

    scenes, input_file = load_scene_plan()
    print(f"已读取 scene_plan.json：{input_file}")

    element_plan = build_element_plan(scenes)
    save_element_plan(element_plan)

    print(f"已生成 element_plan.json：{ROOT_ELEMENT_PLAN_FILE}")
    print(f"已生成下游兼容 element_plan.json：{DATA_CURRENT_ELEMENT_PLAN_FILE}")
    print(f"场景数量：{len(element_plan)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
