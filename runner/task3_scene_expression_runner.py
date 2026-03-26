# -*- coding: utf-8 -*-
"""
runner/task3_scene_expression_runner.py

【Task3：scene_expression_plan 最小安全合并器】

作用：
1. 读取 data/current/scene_plan.json
2. 读取 data/current/expression.json
3. 按顺序进行最小安全合并
4. 生成 data/current/scene_expression_plan.json

合并规则：
- scene[0] 对应 expression.items[0]
- 保留原 scene 结构
- 新增 expression_meta 字段
- 兼容数量不一致情况

边界：
- 不修改任何旧主链文件
- 不接入 timing / assets / tts
- 仅作为外挂合并层
- 仅使用 Python 标准库
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# 允许直接运行时找到项目根目录
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def load_json(file_path: Path) -> Any:
    """读取 JSON 文件"""
    if not file_path.exists():
        raise FileNotFoundError(f"❌ 文件不存在：{file_path}")

    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(file_path: Path, data: Any) -> None:
    """保存 JSON 文件"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_scenes_list(scene_plan_data: Any) -> List[Dict[str, Any]]:
    """
    从 scene_plan.json 中提取 scenes 列表

    兼容：
    A. {"scenes": [...]}
    B. 直接是列表 [...]
    """
    # A. 顶层有 scenes 字段
    if isinstance(scene_plan_data, dict):
        scenes = scene_plan_data.get("scenes")
        if isinstance(scenes, list):
            return scenes

    # B. 直接是列表
    if isinstance(scene_plan_data, list):
        return scene_plan_data

    raise ValueError("❌ scene_plan.json 中未找到有效的 scenes 结构")


def extract_expression_items(expression_data: Any) -> List[Dict[str, Any]]:
    """
    从 expression.json 中提取 expression items 列表

    预期结构：
    {
      "total_items": N,
      "items": [...]
    }
    """
    if isinstance(expression_data, dict):
        items = expression_data.get("items")
        if isinstance(items, list):
            return items

    raise ValueError("❌ expression.json 中未找到有效的 items 结构")


def merge_scenes_with_expressions(
    scenes: List[Dict[str, Any]],
    expression_items: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    按顺序合并 scenes 和 expressions

    返回包含 summary 的合并结果
    """
    merged_scenes: List[Dict[str, Any]] = []
    matched_count = 0
    unmatched_scene_count = 0

    # 合并每个 scene
    for scene_index, scene in enumerate(scenes):
        merged_scene = dict(scene)  # 保留原 scene 结构

        if scene_index < len(expression_items):
            # 该 scene 有对应的 expression
            expr_item = expression_items[scene_index]
            merged_scene["expression_meta"] = {
                "matched": True,
                "expression_index": expr_item.get("index", scene_index),
                "source_text": expr_item.get("source_text", ""),
                "expression": expr_item.get("expression", {}),
            }
            matched_count += 1
        else:
            # 该 scene 没有对应的 expression
            merged_scene["expression_meta"] = {
                "matched": False,
                "reason": "no_expression_item",
            }
            unmatched_scene_count += 1

        merged_scenes.append(merged_scene)

    # 计算多余的 expression
    extra_expression_count = max(0, len(expression_items) - len(scenes))

    result = {
        "source_scene_file": "data/current/scene_plan.json",
        "source_expression_file": "data/current/expression.json",
        "output_file": "data/current/scene_expression_plan.json",
        "scene_count": len(scenes),
        "expression_count": len(expression_items),
        "matched_count": matched_count,
        "unmatched_scene_count": unmatched_scene_count,
        "extra_expression_count": extra_expression_count,
        "scenes": merged_scenes,
    }

    return result


def main() -> None:
    """主执行入口"""
    scene_file = PROJECT_ROOT / "data" / "current" / "scene_plan.json"
    expression_file = PROJECT_ROOT / "data" / "current" / "expression.json"
    output_file = PROJECT_ROOT / "data" / "current" / "scene_expression_plan.json"

    print("=" * 60)
    print("开始执行 Task3：生成 scene_expression_plan.json")
    print("=" * 60)
    print(f"输入文件1：{scene_file}")
    print(f"输入文件2：{expression_file}")
    print(f"输出文件：{output_file}")

    scene_plan_data = load_json(scene_file)
    expression_data = load_json(expression_file)

    scenes = extract_scenes_list(scene_plan_data)
    expression_items = extract_expression_items(expression_data)

    print(f"已提取 scenes 数量：{len(scenes)}")
    print(f"已提取 expression 数量：{len(expression_items)}")

    merged_result = merge_scenes_with_expressions(scenes, expression_items)

    save_json(output_file, merged_result)

    print(f"✅ scene_expression_plan.json 已生成")
    print(f"输出路径：{output_file}")
    print(f"匹配数量：{merged_result['matched_count']}")
    print(f"未匹配 scenes：{merged_result['unmatched_scene_count']}")
    print(f"多余 expressions：{merged_result['extra_expression_count']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
