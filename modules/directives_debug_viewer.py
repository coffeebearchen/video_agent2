# -*- coding: utf-8 -*-
"""
文件名：directives_debug_viewer.py
作用说明：
1. 读取 scene_plan.json
2. 将 scene 中的 directives 结果整理为人类可读报告
3. 输出到固定 txt 文件，便于直接检查

设计边界：
1. 只做观察，不做控制
2. 不改主链，不改 compiled_plan 结构
3. 不读取 VIDEO 层输出
"""

from __future__ import annotations

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_CURRENT_DIR = BASE_DIR / "data" / "current"
ROOT_SCENE_PLAN_FILE = BASE_DIR / "scene_plan.json"
DATA_CURRENT_SCENE_PLAN_FILE = DATA_CURRENT_DIR / "scene_plan.json"
OUTPUT_DIR = BASE_DIR / "output"
REPORT_FILE = OUTPUT_DIR / "directives_debug_report.txt"
DIVIDER = "=" * 60
SECTION_DIVIDER = "-" * 60


def normalize_scene_list(scene_data):
    """兼容 list / dict 两种 scene_plan 结构。"""
    if isinstance(scene_data, list):
        scenes = scene_data
    elif isinstance(scene_data, dict):
        scenes = scene_data.get("scenes", [])
    else:
        scenes = []

    if not isinstance(scenes, list):
        return []

    normalized_scenes = []
    for scene in scenes:
        if isinstance(scene, dict):
            normalized_scenes.append(scene)
        else:
            normalized_scenes.append({})

    return normalized_scenes


def load_scene_plan():
    """优先读取根目录 scene_plan.json，不存在再回退到 data/current。"""
    if ROOT_SCENE_PLAN_FILE.exists():
        input_file = ROOT_SCENE_PLAN_FILE
    elif DATA_CURRENT_SCENE_PLAN_FILE.exists():
        input_file = DATA_CURRENT_SCENE_PLAN_FILE
    else:
        raise FileNotFoundError(
            f"scene_plan.json 不存在：{ROOT_SCENE_PLAN_FILE} 或 {DATA_CURRENT_SCENE_PLAN_FILE}"
        )

    with open(input_file, "r", encoding="utf-8") as file:
        raw_data = json.load(file)

    return normalize_scene_list(raw_data), input_file


def _format_float(value):
    """统一格式化数值字段，非法值回退为空字符串。"""
    try:
        return f"{float(value):.2f}"
    except (TypeError, ValueError):
        return ""


def format_visual_inserts(visual_inserts):
    """将 visual_inserts 转成人类可读文本块。"""
    if not isinstance(visual_inserts, list) or not visual_inserts:
        return "无"

    lines = []
    for index, insert in enumerate(visual_inserts, start=1):
        if not isinstance(insert, dict):
            lines.append(f"{index}. 无效项")
            continue

        file_value = str(insert.get("path", insert.get("file", "")) or "")
        start_value = _format_float(insert.get("start"))
        end_value = _format_float(insert.get("end"))
        position_value = str(insert.get("position", "") or "")
        scale_value = _format_float(insert.get("scale"))
        lines.append(
            f"{index}. file={file_value} | start={start_value} | end={end_value} | "
            f"position={position_value} | scale={scale_value}"
        )

    return "\n".join(lines)


def format_expression_enhancements(enhancements):
    """将 expression_enhancements 转成人类可读文本块。"""
    if not isinstance(enhancements, list) or not enhancements:
        return "无"

    lines = []
    for index, item in enumerate(enhancements, start=1):
        if not isinstance(item, dict):
            lines.append(f"{index}. 无效项")
            continue

        text_value = str(item.get("text", "") or "")
        type_value = str(item.get("type", "") or "")
        start_value = _format_float(item.get("start"))
        end_value = _format_float(item.get("end"))
        position_value = str(item.get("position", "") or "")
        lines.append(
            f"{index}. text={text_value} | type={type_value} | start={start_value} | "
            f"end={end_value} | position={position_value}"
        )

    return "\n".join(lines)


def build_scene_report(scene_item, index):
    """生成单个 scene 的完整调试文本。"""
    scene = scene_item if isinstance(scene_item, dict) else {}
    scene_id = scene.get("scene_id", index)
    role = str(scene.get("role", "") or "")
    scene_type = str(scene.get("type", "") or "")
    text_value = str(scene.get("text", "") or "")
    visual_inserts = scene.get("visual_inserts", [])
    enhancements = scene.get("expression_enhancements", [])

    visual_count = len(visual_inserts) if isinstance(visual_inserts, list) else 0
    enhancement_count = len(enhancements) if isinstance(enhancements, list) else 0

    return "\n".join(
        [
            SECTION_DIVIDER,
            f"Scene {scene_id}",
            SECTION_DIVIDER,
            f"scene_id: {scene_id}",
            f"role: {role}",
            f"type: {scene_type}",
            f"text_length: {len(text_value)}",
            f"visual_inserts_count: {visual_count}",
            f"expression_enhancements_count: {enhancement_count}",
            "",
            "[Text]",
            text_value or "",
            "",
            "[Visual Inserts]",
            format_visual_inserts(visual_inserts),
            "",
            "[Expression Enhancements]",
            format_expression_enhancements(enhancements),
        ]
    )


def build_full_report(scene_list):
    """生成完整调试报告文本。"""
    scenes = normalize_scene_list(scene_list)
    report_blocks = [
        DIVIDER,
        "VIDEO_AGENT｜Directives Debug Report",
        DIVIDER,
        "",
        "[Summary]",
        f"Total Scenes: {len(scenes)}",
        "",
    ]

    for index, scene in enumerate(scenes):
        report_blocks.append(build_scene_report(scene, index))
        report_blocks.append("")

    return "\n".join(report_blocks).rstrip() + "\n"


def save_report(report_text):
    """保存调试报告到固定文件。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(REPORT_FILE, "w", encoding="utf-8") as file:
        file.write(str(report_text or ""))

    return REPORT_FILE


def build_scene_summary(scene_item, index):
    """生成控制台用的 scene 简明摘要。"""
    scene = scene_item if isinstance(scene_item, dict) else {}
    scene_id = scene.get("scene_id", index)
    visual_inserts = scene.get("visual_inserts", [])
    enhancements = scene.get("expression_enhancements", [])

    visual_count = len(visual_inserts) if isinstance(visual_inserts, list) else 0
    enhancement_count = len(enhancements) if isinstance(enhancements, list) else 0
    return f"scene={scene_id} | visual_inserts={visual_count} | enhancements={enhancement_count}"
