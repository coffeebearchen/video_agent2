# -*- coding: utf-8 -*-
"""
runner/task5_timing_plan_runner.py

【Task5：timing_plan_v2 最小安全执行器】

作用：
1. 读取 data/current/style_plan.json
2. 提取每个 item 的 style_mode 与 pace
3. 映射为节奏控制参数
4. 生成 data/current/timing_plan_v2.json

边界：
- 不修改任何旧主链文件
- 不修改原 timing_plan.json
- 仅作为外挂 timing 规划层
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


TIMING_MAPPING: Dict[str, Dict[str, Any]] = {
    "hook": {
        "base_duration": 4.0,
        "pause_before": 0.3,
        "pause_after": 0.6,
        "transition_duration": 0.4,
        "rhythm_mode": "hook",
    },
    "explain": {
        "base_duration": 3.5,
        "pause_before": 0.1,
        "pause_after": 0.2,
        "transition_duration": 0.3,
        "rhythm_mode": "steady",
    },
    "conclude": {
        "base_duration": 4.2,
        "pause_before": 0.2,
        "pause_after": 0.8,
        "transition_duration": 0.35,
        "rhythm_mode": "close",
    },
    "emphasize": {
        "base_duration": 3.2,
        "pause_before": 0.15,
        "pause_after": 0.35,
        "transition_duration": 0.25,
        "rhythm_mode": "accent",
    },
    "bridge": {
        "base_duration": 2.8,
        "pause_before": 0.05,
        "pause_after": 0.1,
        "transition_duration": 0.2,
        "rhythm_mode": "bridge",
    },
    "default": {
        "base_duration": 3.0,
        "pause_before": 0.1,
        "pause_after": 0.2,
        "transition_duration": 0.3,
        "rhythm_mode": "default",
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



def extract_items(data: Any) -> List[Dict[str, Any]]:
    """从 style_plan.json 中提取 items 列表"""
    if isinstance(data, dict):
        items = data.get("items")
        if isinstance(items, list):
            return items

    raise ValueError("❌ style_plan.json 中未找到有效的 items 结构")



def resolve_timing(style_mode: Any) -> Dict[str, Any]:
    """根据 style_mode 获取 timing 映射"""
    if not isinstance(style_mode, str):
        return dict(TIMING_MAPPING["default"])

    return dict(TIMING_MAPPING.get(style_mode, TIMING_MAPPING["default"]))



def build_timing_items(style_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """把每个 style item 映射为 timing item"""
    timing_items: List[Dict[str, Any]] = []

    for item in style_items:
        style_mode = item.get("style_mode", "default")
        timing_fields = resolve_timing(style_mode)

        timing_item = {
            "scene_id": item.get("scene_id"),
            "role": item.get("role", ""),
            "type": item.get("type", ""),
            "style_mode": style_mode,
            "pace": item.get("pace", "normal"),
            "base_duration": timing_fields["base_duration"],
            "pause_before": timing_fields["pause_before"],
            "pause_after": timing_fields["pause_after"],
            "transition_duration": timing_fields["transition_duration"],
            "rhythm_mode": timing_fields["rhythm_mode"],
        }
        timing_items.append(timing_item)

    return timing_items



def main() -> None:
    """主执行入口"""
    input_file = PROJECT_ROOT / "data" / "current" / "style_plan.json"
    output_file = PROJECT_ROOT / "data" / "current" / "timing_plan_v2.json"

    print("=" * 60)
    print("开始执行 Task5：生成 timing_plan_v2.json")
    print("=" * 60)
    print(f"输入文件：{input_file}")
    print(f"输出文件：{output_file}")

    input_data = load_json(input_file)
    style_items = extract_items(input_data)
    timing_items = build_timing_items(style_items)

    output_data = {
        "source_file": "data/current/style_plan.json",
        "output_file": "data/current/timing_plan_v2.json",
        "scene_count": len(style_items),
        "items": timing_items,
    }

    save_json(output_file, output_data)

    print("✅ timing_plan_v2.json 已生成")
    print(f"输出路径：{output_file}")
    print(f"场景数量：{len(style_items)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
