# -*- coding: utf-8 -*-
"""
runner/task6_visual_plan_runner.py

【Task6：visual_plan 最小安全执行器】

作用：
1. 读取 data/current/style_plan.json
2. 读取 data/current/timing_plan_v2.json
3. 按 scene_id 优先匹配 style 与 timing 信息
4. 映射为视觉策略
5. 生成 data/current/visual_plan.json

边界：
- 不修改任何旧主链文件
- 不接入 assets / tts / render
- 仅作为外挂 visual 规划层
- 仅使用 Python 标准库
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# 允许直接运行时找到项目根目录
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


VISUAL_MAPPING: Dict[str, Dict[str, str]] = {
    "hook": {
        "visual_mode": "title_focus",
        "asset_preference": "text_card",
        "text_layout": "large_center",
        "motion_hint": "slow_push",
        "highlight_strategy": "keyword_focus",
    },
    "explain": {
        "visual_mode": "balanced_explain",
        "asset_preference": "mixed",
        "text_layout": "top_bottom_split",
        "motion_hint": "steady_hold",
        "highlight_strategy": "line_balance",
    },
    "conclude": {
        "visual_mode": "summary_close",
        "asset_preference": "summary_card",
        "text_layout": "center_stack",
        "motion_hint": "hold_close",
        "highlight_strategy": "final_emphasis",
    },
    "emphasize": {
        "visual_mode": "highlight_focus",
        "asset_preference": "text_highlight",
        "text_layout": "center_focus",
        "motion_hint": "pulse_focus",
        "highlight_strategy": "strong_keyword",
    },
    "bridge": {
        "visual_mode": "transition_bridge",
        "asset_preference": "b_roll",
        "text_layout": "minimal_corner",
        "motion_hint": "quick_cut",
        "highlight_strategy": "none",
    },
    "default": {
        "visual_mode": "default_visual",
        "asset_preference": "mixed",
        "text_layout": "standard",
        "motion_hint": "steady_hold",
        "highlight_strategy": "line_balance",
    },
}


TIMING_DEFAULTS: Dict[str, Any] = {
    "base_duration": 3.0,
    "pause_before": 0.1,
    "pause_after": 0.2,
    "transition_duration": 0.3,
    "rhythm_mode": "default",
}


STYLE_DEFAULTS: Dict[str, Any] = {
    "style_mode": "default",
    "pace": "normal",
    "emphasis_level": "medium",
    "transition_hint": "none",
    "visual_hint": "balanced",
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



def extract_items(data: Any, file_label: str) -> List[Dict[str, Any]]:
    """从输入结构中提取 items 列表"""
    if isinstance(data, dict):
        items = data.get("items")
        if isinstance(items, list):
            return items

    raise ValueError(f"❌ {file_label} 中未找到有效的 items 结构")



def resolve_visual(style_mode: Any) -> Dict[str, str]:
    """根据 style_mode 获取视觉映射"""
    if not isinstance(style_mode, str):
        return dict(VISUAL_MAPPING["default"])

    return dict(VISUAL_MAPPING.get(style_mode, VISUAL_MAPPING["default"]))



def build_timing_lookup(timing_items: List[Dict[str, Any]]) -> Dict[Any, Dict[str, Any]]:
    """为 timing items 建立 scene_id 索引"""
    lookup: Dict[Any, Dict[str, Any]] = {}

    for item in timing_items:
        scene_id = item.get("scene_id")
        if scene_id is not None and scene_id not in lookup:
            lookup[scene_id] = item

    return lookup



def find_timing_item(
    style_item: Dict[str, Any],
    style_index: int,
    timing_lookup: Dict[Any, Dict[str, Any]],
    timing_items: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """按 scene_id 优先、按顺序兜底匹配 timing item"""
    scene_id = style_item.get("scene_id")
    if scene_id is not None and scene_id in timing_lookup:
        return timing_lookup[scene_id]

    if style_index < len(timing_items):
        return timing_items[style_index]

    return None



def build_visual_items(
    style_items: List[Dict[str, Any]],
    timing_items: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """合并 style 与 timing 信息并生成 visual items"""
    items: List[Dict[str, Any]] = []
    timing_lookup = build_timing_lookup(timing_items)

    for index, style_item in enumerate(style_items):
        timing_item = find_timing_item(style_item, index, timing_lookup, timing_items) or {}

        style_mode = style_item.get("style_mode", STYLE_DEFAULTS["style_mode"])
        visual_fields = resolve_visual(style_mode)

        item = {
            "scene_id": style_item.get("scene_id", timing_item.get("scene_id")),
            "role": style_item.get("role", timing_item.get("role", "")),
            "type": style_item.get("type", timing_item.get("type", "")),
            "style_mode": style_mode,
            "pace": style_item.get("pace", timing_item.get("pace", STYLE_DEFAULTS["pace"])),
            "emphasis_level": style_item.get("emphasis_level", STYLE_DEFAULTS["emphasis_level"]),
            "transition_hint": style_item.get("transition_hint", STYLE_DEFAULTS["transition_hint"]),
            "visual_hint": style_item.get("visual_hint", STYLE_DEFAULTS["visual_hint"]),
            "base_duration": timing_item.get("base_duration", TIMING_DEFAULTS["base_duration"]),
            "pause_before": timing_item.get("pause_before", TIMING_DEFAULTS["pause_before"]),
            "pause_after": timing_item.get("pause_after", TIMING_DEFAULTS["pause_after"]),
            "transition_duration": timing_item.get(
                "transition_duration", TIMING_DEFAULTS["transition_duration"]
            ),
            "rhythm_mode": timing_item.get("rhythm_mode", TIMING_DEFAULTS["rhythm_mode"]),
            "visual_mode": visual_fields["visual_mode"],
            "asset_preference": visual_fields["asset_preference"],
            "text_layout": visual_fields["text_layout"],
            "motion_hint": visual_fields["motion_hint"],
            "highlight_strategy": visual_fields["highlight_strategy"],
        }
        items.append(item)

    return items



def main() -> None:
    """主执行入口"""
    style_file = PROJECT_ROOT / "data" / "current" / "style_plan.json"
    timing_file = PROJECT_ROOT / "data" / "current" / "timing_plan_v2.json"
    output_file = PROJECT_ROOT / "data" / "current" / "visual_plan.json"

    print("=" * 60)
    print("开始执行 Task6：生成 visual_plan.json")
    print("=" * 60)
    print(f"输入文件1：{style_file}")
    print(f"输入文件2：{timing_file}")
    print(f"输出文件：{output_file}")

    style_data = load_json(style_file)
    timing_data = load_json(timing_file)

    style_items = extract_items(style_data, "style_plan.json")
    timing_items = extract_items(timing_data, "timing_plan_v2.json")
    visual_items = build_visual_items(style_items, timing_items)

    output_data = {
        "source_style_file": "data/current/style_plan.json",
        "source_timing_file": "data/current/timing_plan_v2.json",
        "output_file": "data/current/visual_plan.json",
        "scene_count": len(style_items),
        "items": visual_items,
    }

    save_json(output_file, output_data)

    print("✅ visual_plan.json 已生成")
    print(f"输出路径：{output_file}")
    print(f"场景数量：{len(style_items)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
