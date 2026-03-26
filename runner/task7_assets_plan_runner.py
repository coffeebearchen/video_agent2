# -*- coding: utf-8 -*-
"""
runner/task7_assets_plan_runner.py

【Task7：assets_plan_v2 最小安全执行器】

作用：
1. 读取 data/current/visual_plan.json
2. 提取每个 scene 的 visual 策略字段
3. 映射为素材策略
4. 生成 data/current/assets_plan_v2.json

边界：
- 不修改任何旧主链文件
- 不读取本地素材目录
- 不调用 asset_selector.py
- 仅作为外挂 assets 规划层
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


ASSET_MAPPING: Dict[str, Dict[str, str]] = {
    "title_focus": {
        "asset_mode": "text_card_only",
        "primary_asset_type": "text_card",
        "secondary_asset_type": "background_image",
        "overlay_strategy": "title_overlay",
        "asset_density": "low",
        "selection_hint": "clean_background",
    },
    "balanced_explain": {
        "asset_mode": "mixed_explain",
        "primary_asset_type": "image_or_clip",
        "secondary_asset_type": "text_card",
        "overlay_strategy": "split_explain",
        "asset_density": "medium",
        "selection_hint": "topic_relevant",
    },
    "summary_close": {
        "asset_mode": "summary_card",
        "primary_asset_type": "summary_card",
        "secondary_asset_type": "background_texture",
        "overlay_strategy": "center_summary",
        "asset_density": "low",
        "selection_hint": "clean_close",
    },
    "highlight_focus": {
        "asset_mode": "highlight_card",
        "primary_asset_type": "text_highlight_card",
        "secondary_asset_type": "background_image",
        "overlay_strategy": "highlight_overlay",
        "asset_density": "low",
        "selection_hint": "contrast_focus",
    },
    "transition_bridge": {
        "asset_mode": "broll_bridge",
        "primary_asset_type": "b_roll_clip",
        "secondary_asset_type": "minimal_text",
        "overlay_strategy": "corner_label",
        "asset_density": "high",
        "selection_hint": "motion_first",
    },
    "default": {
        "asset_mode": "default_assets",
        "primary_asset_type": "image_or_clip",
        "secondary_asset_type": "text_card",
        "overlay_strategy": "standard_overlay",
        "asset_density": "medium",
        "selection_hint": "general_relevant",
    },
}


VISUAL_DEFAULTS: Dict[str, Any] = {
    "visual_mode": "default_visual",
    "asset_preference": "mixed",
    "text_layout": "standard",
    "motion_hint": "steady_hold",
    "highlight_strategy": "line_balance",
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



def extract_items(data: Any) -> List[Dict[str, Any]]:
    """从 visual_plan.json 中提取 items 列表"""
    if isinstance(data, dict):
        items = data.get("items")
        if isinstance(items, list):
            return items

    raise ValueError("❌ visual_plan.json 中未找到有效的 items 结构")



def resolve_asset_plan(visual_mode: Any) -> Dict[str, str]:
    """根据 visual_mode 获取素材映射"""
    if not isinstance(visual_mode, str):
        return dict(ASSET_MAPPING["default"])

    return dict(ASSET_MAPPING.get(visual_mode, ASSET_MAPPING["default"]))



def build_asset_items(visual_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """把每个 visual item 映射为 assets item"""
    items: List[Dict[str, Any]] = []

    for visual_item in visual_items:
        visual_mode = visual_item.get("visual_mode", VISUAL_DEFAULTS["visual_mode"])
        asset_fields = resolve_asset_plan(visual_mode)

        item = {
            "scene_id": visual_item.get("scene_id"),
            "role": visual_item.get("role", ""),
            "type": visual_item.get("type", ""),
            "visual_mode": visual_mode,
            "asset_preference": visual_item.get(
                "asset_preference", VISUAL_DEFAULTS["asset_preference"]
            ),
            "text_layout": visual_item.get("text_layout", VISUAL_DEFAULTS["text_layout"]),
            "motion_hint": visual_item.get("motion_hint", VISUAL_DEFAULTS["motion_hint"]),
            "highlight_strategy": visual_item.get(
                "highlight_strategy", VISUAL_DEFAULTS["highlight_strategy"]
            ),
            "asset_mode": asset_fields["asset_mode"],
            "primary_asset_type": asset_fields["primary_asset_type"],
            "secondary_asset_type": asset_fields["secondary_asset_type"],
            "overlay_strategy": asset_fields["overlay_strategy"],
            "asset_density": asset_fields["asset_density"],
            "selection_hint": asset_fields["selection_hint"],
        }
        items.append(item)

    return items



def main() -> None:
    """主执行入口"""
    input_file = PROJECT_ROOT / "data" / "current" / "visual_plan.json"
    output_file = PROJECT_ROOT / "data" / "current" / "assets_plan_v2.json"

    print("=" * 60)
    print("开始执行 Task7：生成 assets_plan_v2.json")
    print("=" * 60)
    print(f"输入文件：{input_file}")
    print(f"输出文件：{output_file}")

    input_data = load_json(input_file)
    visual_items = extract_items(input_data)
    asset_items = build_asset_items(visual_items)

    output_data = {
        "source_file": "data/current/visual_plan.json",
        "output_file": "data/current/assets_plan_v2.json",
        "scene_count": len(visual_items),
        "items": asset_items,
    }

    save_json(output_file, output_data)

    print("✅ assets_plan_v2.json 已生成")
    print(f"输出路径：{output_file}")
    print(f"场景数量：{len(visual_items)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
