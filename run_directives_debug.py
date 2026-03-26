# -*- coding: utf-8 -*-
"""
Directives Debug Viewer 独立运行入口。

职责：
1. 读取当前 scene_plan.json
2. 生成 directives 调试报告
3. 保存到固定输出文件
4. 在控制台打印简明摘要
"""

import json

from modules import project_paths
from modules.directives_debug_viewer import (
    DIVIDER,
    build_full_report,
    build_scene_summary,
    normalize_scene_list,
)


SCENE_PLAN_JSON_PATH = getattr(
    project_paths,
    "SCENE_PLAN_JSON_PATH",
    project_paths.get_project_root() / "scene_plan.json",
)
CURRENT_SCENE_PLAN_JSON_PATH = getattr(
    project_paths,
    "CURRENT_SCENE_PLAN_JSON_PATH",
    project_paths.get_data_current_dir() / "scene_plan.json",
)
OUTPUT_DIR = getattr(
    project_paths,
    "OUTPUT_DIR",
    project_paths.get_project_root() / "output",
)
REPORT_FILE_PATH = getattr(
    project_paths,
    "DIRECTIVES_DEBUG_REPORT_PATH",
    OUTPUT_DIR / "directives_debug_report.txt",
)


def resolve_scene_plan_input_path():
    """优先读取根目录 scene_plan.json，不存在再回退到 data/current。"""
    print(f"[DirectivesDebug] 开始检查 scene_plan.json：{SCENE_PLAN_JSON_PATH}")
    if SCENE_PLAN_JSON_PATH.exists():
        return SCENE_PLAN_JSON_PATH

    print(f"[DirectivesDebug] 根目录 scene_plan.json 不存在，回退检查：{CURRENT_SCENE_PLAN_JSON_PATH}")
    if CURRENT_SCENE_PLAN_JSON_PATH.exists():
        return CURRENT_SCENE_PLAN_JSON_PATH

    raise FileNotFoundError(
        f"scene_plan.json 不存在：{SCENE_PLAN_JSON_PATH} 或 {CURRENT_SCENE_PLAN_JSON_PATH}"
    )


def load_scene_plan_from_path(scene_plan_path):
    """按统一路径读取 scene_plan.json。"""
    with open(scene_plan_path, "r", encoding="utf-8") as file:
        raw_data = json.load(file)

    scene_list = normalize_scene_list(raw_data)
    print(f"[DirectivesDebug] 已读取 scene_plan.json：{scene_plan_path}")
    return scene_list


def save_report_to_path(report_text):
    """按统一路径写出调试报告。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with open(REPORT_FILE_PATH, "w", encoding="utf-8") as file:
        file.write(str(report_text or ""))

    print(f"[DirectivesDebug] 已输出调试报告：{REPORT_FILE_PATH}")
    return REPORT_FILE_PATH


def main():
    print(DIVIDER)
    print("开始生成 Directives Debug Report...")
    print(DIVIDER)

    input_file = resolve_scene_plan_input_path()
    scene_list = load_scene_plan_from_path(input_file)
    report_text = build_full_report(scene_list)
    report_file = save_report_to_path(report_text)

    print(f"已读取 scene_plan.json：{input_file}")
    print(f"Scene 数量：{len(scene_list)}")
    for index, scene_item in enumerate(scene_list):
        print(build_scene_summary(scene_item, index))
    print(f"已输出调试报告：{report_file}")
    print(DIVIDER)


if __name__ == "__main__":
    main()