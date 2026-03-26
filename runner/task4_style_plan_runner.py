# -*- coding: utf-8 -*-
"""
runner/task4_style_plan_runner.py

【Task4：style_plan 最小安全执行器】

作用：
1. 读取 data/current/scene_expression_plan.json
2. 提取每个 scene 的 expression_meta
3. 映射为表现策略
4. 生成 data/current/style_plan.json

边界：
- 不修改任何旧主链文件
- 不接入 timing / assets / tts
- 仅作为外挂 style 规划层
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


STYLE_MAPPING: Dict[str, Dict[str, str]] = {
    "question": {
        "style_mode": "hook",
        "pace": "slow",
        "emphasis_level": "high",
        "transition_hint": "pause_after",
        "visual_hint": "focus_text",
    },
    "concept": {
        "style_mode": "explain",
        "pace": "normal",
        "emphasis_level": "medium",
        "transition_hint": "none",
        "visual_hint": "balanced",
    },
    "conclusion": {
        "style_mode": "conclude",
        "pace": "steady",
        "emphasis_level": "high",
        "transition_hint": "hold_end",
        "visual_hint": "summary_focus",
    },
    "emphasis": {
        "style_mode": "emphasize",
        "pace": "normal",
        "emphasis_level": "high",
        "transition_hint": "flash_point",
        "visual_hint": "highlight_text",
    },
    "transition": {
        "style_mode": "bridge",
        "pace": "fast",
        "emphasis_level": "medium",
        "transition_hint": "cut_next",
        "visual_hint": "shift_scene",
    },
    "default": {
        "style_mode": "default",
        "pace": "normal",
        "emphasis_level": "medium",
        "transition_hint": "none",
        "visual_hint": "balanced",
    },
}


def load_json(file_path: Path) -> Any:
    """读取 JSON 文件"""
    if not file_path.exists():
        raise FileNotFoundError(f"❌ 文件不存在：{file_path}")

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)



def save_json(file_path: Path, data: Any) -> None:
    """保存 JSON 文件"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)



def extract_scenes(data: Any) -> List[Dict[str, Any]]:
    """从输入结构中提取 scenes 列表"""
    if isinstance(data, dict):
        scenes = data.get("scenes")
        if isinstance(scenes, list):
            return scenes

    raise ValueError("❌ scene_expression_plan.json 中未找到有效的 scenes 结构")



def resolve_style(expression_meta: Dict[str, Any]) -> Dict[str, str]:
    """根据 expression_meta 解析 style 映射"""
    if not isinstance(expression_meta, dict):
        return dict(STYLE_MAPPING["default"])

    if not expression_meta.get("matched"):
        return dict(STYLE_MAPPING["default"])

    expression = expression_meta.get("expression")
    if not isinstance(expression, dict):
        return dict(STYLE_MAPPING["default"])

    expression_type = expression.get("expression_type")
    if not isinstance(expression_type, str):
        return dict(STYLE_MAPPING["default"])

    return dict(STYLE_MAPPING.get(expression_type, STYLE_MAPPING["default"]))



def build_style_items(scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """把每个 scene 映射为 style_plan item"""
    items: List[Dict[str, Any]] = []

    for scene in scenes:
        expression_meta = scene.get("expression_meta", {})
        expression = expression_meta.get("expression", {}) if isinstance(expression_meta, dict) else {}

        expression_type = "default"
        carrier = "voice"
        confidence = 0.0

        if isinstance(expression, dict):
            expression_type = expression.get("expression_type", "default")
            carrier = expression.get("carrier", "voice")
            confidence = expression.get("confidence", 0.0)

        style_fields = resolve_style(expression_meta if isinstance(expression_meta, dict) else {})

        item = {
            "scene_id": scene.get("scene_id"),
            "role": scene.get("role", ""),
            "type": scene.get("type", ""),
            "expression_type": expression_type,
            "carrier": carrier,
            "confidence": confidence,
            "style_mode": style_fields["style_mode"],
            "pace": style_fields["pace"],
            "emphasis_level": style_fields["emphasis_level"],
            "transition_hint": style_fields["transition_hint"],
            "visual_hint": style_fields["visual_hint"],
        }
        items.append(item)

    return items



def main() -> None:
    """主执行入口"""
    input_file = PROJECT_ROOT / "data" / "current" / "scene_expression_plan.json"
    output_file = PROJECT_ROOT / "data" / "current" / "style_plan.json"

    print("=" * 60)
    print("开始执行 Task4：生成 style_plan.json")
    print("=" * 60)
    print(f"输入文件：{input_file}")
    print(f"输出文件：{output_file}")

    input_data = load_json(input_file)
    scenes = extract_scenes(input_data)
    items = build_style_items(scenes)

    output_data = {
        "source_file": "data/current/scene_expression_plan.json",
        "output_file": "data/current/style_plan.json",
        "scene_count": len(scenes),
        "items": items,
    }

    save_json(output_file, output_data)

    print("✅ style_plan.json 已生成")
    print(f"输出路径：{output_file}")
    print(f"场景数量：{len(scenes)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
