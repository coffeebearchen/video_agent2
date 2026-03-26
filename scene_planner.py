# -*- coding: utf-8 -*-
"""
scene_planner.py

【Scene Planner V1｜冻结版】

职责：
1. 读取 script.json
2. 提取 hook / explanation / conclusion
3. 生成固定 3 个 scene 的骨架结构
4. 写出 scene_plan.json

注意：
- 本模块只处理 SCRIPT → SCENE
- 不做智能分镜
- 不做素材匹配
- 不做时间轴与渲染逻辑
"""

import json

from modules import project_paths
from modules.auto_directives_generator import (
    DEFAULT_STYLE_PRESET,
    generate_auto_directives,
    normalize_style_preset,
)
from modules.config_loader import load_runtime_config
from modules.script_directives_parser import parse_script_directives


SCRIPT_JSON_PATH = getattr(
    project_paths,
    "SCRIPT_JSON_PATH",
    project_paths.get_project_root() / "script.json",
)
SCENE_PLAN_JSON_PATH = getattr(
    project_paths,
    "SCENE_PLAN_JSON_PATH",
    project_paths.get_project_root() / "scene_plan.json",
)
DATA_CURRENT_DIR = getattr(
    project_paths,
    "DATA_CURRENT_DIR",
    project_paths.get_data_current_dir(),
)
CURRENT_SCENE_PLAN_JSON_PATH = getattr(
    project_paths,
    "CURRENT_SCENE_PLAN_JSON_PATH",
    DATA_CURRENT_DIR / "scene_plan.json",
)
ensure_core_directories = getattr(
    project_paths,
    "ensure_core_directories",
    project_paths.ensure_standard_directories,
)


def load_script_json():
    """读取 script.json，不存在时抛出清晰中文错误。"""
    print(f"[ScenePlanner] 准备读取 script.json：{SCRIPT_JSON_PATH}")
    if not SCRIPT_JSON_PATH.exists():
        raise FileNotFoundError(f"script.json 不存在：{SCRIPT_JSON_PATH}")

    with open(SCRIPT_JSON_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def extract_script_sections(script_data):
    """从 script 数据中提取 hook / explanation / conclusion，缺字段时温和兜底。"""
    hook = str(script_data.get("hook", "") or "").strip()
    explanation = str(script_data.get("explanation", "") or "").strip()
    conclusion = str(script_data.get("conclusion", "") or "").strip()

    cards = script_data.get("cards", [])
    if isinstance(cards, list):
        for card in cards:
            if not isinstance(card, dict):
                continue

            card_type = str(card.get("type", "") or "").strip().lower()
            card_text = str(card.get("text", "") or "").strip()

            if not hook and card_type == "hook":
                hook = card_text
            elif not explanation and card_type == "explanation":
                explanation = card_text
            elif not conclusion and card_type == "conclusion":
                conclusion = card_text

    # 兼容极简 cards 结构：按顺序兜底抽取前三段
    ordered_card_texts = []
    if isinstance(cards, list):
        for card in cards:
            if isinstance(card, dict):
                ordered_card_texts.append(str(card.get("text", "") or "").strip())

    if not hook and len(ordered_card_texts) >= 1:
        hook = ordered_card_texts[0]
    if not explanation and len(ordered_card_texts) >= 2:
        explanation = ordered_card_texts[1]
    if not conclusion and len(ordered_card_texts) >= 3:
        conclusion = ordered_card_texts[2]

    return hook, explanation, conclusion


def extract_script_style_preset(script_data):
    """从 script.json 顶层提取 style preset 原始值。"""
    if not isinstance(script_data, dict):
        return ""

    style_value = script_data.get("style")
    if isinstance(style_value, dict):
        preset = str(style_value.get("preset", "") or "").strip().lower()
        return preset

    return ""


def resolve_style_preset(script_data, runtime_config_result):
    """按 config.json > script.json > default 的顺序解析 style preset。"""
    config_data = runtime_config_result.get("config", {})
    meta_data = runtime_config_result.get("meta", {})
    provided = meta_data.get("provided", {})

    if provided.get("style.preset"):
        preset = str(
            config_data.get("style", {}).get("preset", DEFAULT_STYLE_PRESET)
        ).strip().lower() or DEFAULT_STYLE_PRESET
        return preset, [f"style preset 来源：config.json -> {preset}"]

    script_preset = extract_script_style_preset(script_data)
    if script_preset:
        normalized_preset, fallback_used = normalize_style_preset(script_preset)
        logs = []
        if fallback_used:
            logs.append(f"script.json style.preset 非法，已回退 {DEFAULT_STYLE_PRESET}")
        logs.append(f"style preset 来源：script.json -> {normalized_preset}")
        return normalized_preset, logs

    return DEFAULT_STYLE_PRESET, [f"style preset 未提供，已使用默认值 {DEFAULT_STYLE_PRESET}"]


def build_scene_plan(
    hook,
    explanation,
    conclusion,
    style_preset=DEFAULT_STYLE_PRESET,
    auto_enabled=True,
    max_auto_inserts=2,
):
    """构建固定 3 个 scene 的冻结版骨架结构。"""
    scene_specs = [
        (0, "intro", "overlay", hook),
        (1, "body", "explain", explanation),
        (2, "outro", "card", conclusion),
    ]

    scene_plan = []
    for scene_id, role, scene_type, raw_text in scene_specs:
        parsed_directives = parse_script_directives(raw_text)
        stats = parsed_directives.get("stats", {})
        ignored_details = parsed_directives.get("ignored_details", [])
        directive_logs = parsed_directives.get("logs", [])
        cleaned_text = parsed_directives.get("text", "")
        visual_inserts = parsed_directives.get("visual_inserts", [])
        expression_enhancements = parsed_directives.get("expression_enhancements", [])

        auto_directives = generate_auto_directives(
            text=cleaned_text,
            existing_visual_inserts=visual_inserts,
            existing_enhancements=expression_enhancements,
            style_preset=style_preset,
            auto_enabled=auto_enabled,
            max_auto_inserts=max_auto_inserts,
        )
        auto_logs = auto_directives.get("logs", [])
        if not visual_inserts:
            visual_inserts = auto_directives.get("visual_inserts", [])
        if not expression_enhancements:
            expression_enhancements = auto_directives.get("expression_enhancements", [])

        scene_item = {
            "scene_id": scene_id,
            "role": role,
            "type": scene_type,
            "text": cleaned_text,
        }

        for log_line in directive_logs:
            print(f"[Directives] scene={scene_id} {log_line}")
        for log_line in auto_logs:
            print(f"[AutoDirectives] scene={scene_id} {log_line}")

        print(
            f"[Directives] scene={scene_id} 检测到 script_directives："
            f"{stats.get('total_directives', 0)} 条"
        )

        if visual_inserts:
            scene_item["visual_inserts"] = visual_inserts
        print(
            f"[Directives] scene={scene_id} 已注入 visual_inserts："
            f"{len(visual_inserts)} 项"
        )

        if expression_enhancements:
            scene_item["expression_enhancements"] = expression_enhancements
        print(
            f"[Directives] scene={scene_id} 已注入 expression_enhancements："
            f"{len(expression_enhancements)} 项"
        )

        ignored_count = stats.get("ignored_directives", 0)
        if ignored_count > 0:
            ignored_reason_summary = "；".join(
                f"{item.get('directive', '')} -> {item.get('reason', '')}"
                for item in ignored_details[:3]
            )
            print(f"[Directives] scene={scene_id} 忽略非法指令：{ignored_count} 条")
            if ignored_reason_summary:
                print(f"[Directives] scene={scene_id} 忽略原因：{ignored_reason_summary}")

        preview_text = cleaned_text[:36]
        if len(cleaned_text) > 36:
            preview_text = f"{preview_text}..."
        print(f"[Directives] scene={scene_id} 清洗后文本：{preview_text}")

        scene_plan.append(scene_item)

    return scene_plan


def save_scene_plan(scene_plan):
    """写出 scene_plan.json，并同时保存下游兼容版本。"""
    print(f"[ScenePlanner] 准备写出 scene_plan.json：{SCENE_PLAN_JSON_PATH}")
    print(f"[ScenePlanner] 准备写出下游兼容 scene_plan.json：{CURRENT_SCENE_PLAN_JSON_PATH}")
    ensure_core_directories()
    DATA_CURRENT_DIR.mkdir(parents=True, exist_ok=True)

    with open(SCENE_PLAN_JSON_PATH, "w", encoding="utf-8") as file:
        json.dump(scene_plan, file, ensure_ascii=False, indent=2)

    downstream_plan = {
        "scenes": scene_plan
    }
    with open(CURRENT_SCENE_PLAN_JSON_PATH, "w", encoding="utf-8") as file:
        json.dump(downstream_plan, file, ensure_ascii=False, indent=2)


def main():
    print("=" * 60)
    print("开始生成 Scene Planner V1...")
    print("=" * 60)
    print("[ScenePlanner] 开始检查核心目录...")
    ensure_core_directories()
    print(f"[ScenePlanner] 核心目录已就绪：{DATA_CURRENT_DIR}")

    script_data = load_script_json()
    runtime_config_result = load_runtime_config()
    for log_line in runtime_config_result.get("logs", []):
        print(f"[Config] {log_line}")

    hook, explanation, conclusion = extract_script_sections(script_data)
    style_preset, style_logs = resolve_style_preset(script_data, runtime_config_result)
    for log_line in style_logs:
        print(f"[Config] {log_line}")

    runtime_config = runtime_config_result.get("config", {})
    auto_enabled = runtime_config.get("auto_directives", {}).get("enabled", True)
    max_auto_inserts = runtime_config.get("insert_policy", {}).get("max_per_scene", 2)
    scene_plan = build_scene_plan(
        hook,
        explanation,
        conclusion,
        style_preset=style_preset,
        auto_enabled=auto_enabled,
        max_auto_inserts=max_auto_inserts,
    )
    save_scene_plan(scene_plan)

    print(f"已生成 scene_plan.json：{SCENE_PLAN_JSON_PATH}")
    print(f"已生成下游兼容 scene_plan.json：{CURRENT_SCENE_PLAN_JSON_PATH}")
    print(f"场景数量：{len(scene_plan)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
