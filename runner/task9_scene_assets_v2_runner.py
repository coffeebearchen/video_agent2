# -*- coding: utf-8 -*-
"""
runner/task9_scene_assets_v2_runner.py

【Task9：scene_assets_v2 最小安全执行器】

作用：
1. 读取 data/current/resolved_assets_plan.json
2. 转换为主链兼容的 scene_assets_v2 结构
3. 生成 data/current/scene_assets_v2.json

边界：
- 不修改任何旧主链文件
- 不修改旧的 scene_assets.json 逻辑
- 仅作为兼容转换层
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

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)



def save_json(file_path: Path, data: Any) -> None:
    """保存 JSON 文件"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)



def extract_items(data: Any) -> List[Dict[str, Any]]:
    """从 resolved_assets_plan.json 中提取 items 列表"""
    if isinstance(data, dict):
        items = data.get("items")
        if isinstance(items, list):
            return items

    raise ValueError("❌ resolved_assets_plan.json 中未找到有效的 items 结构")



def build_assets_list(item: Dict[str, Any]) -> List[Dict[str, str]]:
    """把 primary / secondary 路径转换为 assets 数组"""
    assets: List[Dict[str, str]] = []

    primary_asset_path = item.get("primary_asset_path", "")
    secondary_asset_path = item.get("secondary_asset_path", "")

    if isinstance(primary_asset_path, str) and primary_asset_path:
        assets.append({
            "type": "primary",
            "path": primary_asset_path,
        })

    if isinstance(secondary_asset_path, str) and secondary_asset_path:
        assets.append({
            "type": "secondary",
            "path": secondary_asset_path,
        })

    return assets



def build_scene_assets_items(resolved_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """把 resolved assets items 转换为 scene_assets_v2 items"""
    items: List[Dict[str, Any]] = []

    for item in resolved_items:
        primary_asset_path = item.get("primary_asset_path", "")
        fallback = not (isinstance(primary_asset_path, str) and primary_asset_path)

        scene_item = {
            "scene_id": item.get("scene_id"),
            "role": item.get("role", ""),
            "type": item.get("type", ""),
            "assets": build_assets_list(item),
            "fallback": fallback,
        }
        items.append(scene_item)

    return items



def main() -> None:
    """主执行入口"""
    input_file = PROJECT_ROOT / "data" / "current" / "resolved_assets_plan.json"
    output_file = PROJECT_ROOT / "data" / "current" / "scene_assets_v2.json"

    print("=" * 60)
    print("开始执行 Task9：生成 scene_assets_v2.json")
    print("=" * 60)
    print(f"输入文件：{input_file}")
    print(f"输出文件：{output_file}")

    input_data = load_json(input_file)
    resolved_items = extract_items(input_data)
    scene_assets_items = build_scene_assets_items(resolved_items)

    output_data = {
        "scene_count": len(scene_assets_items),
        "items": scene_assets_items,
    }

    save_json(output_file, output_data)

    print("✅ scene_assets_v2.json 已生成")
    print(f"输出路径：{output_file}")
    print(f"场景数量：{len(scene_assets_items)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
