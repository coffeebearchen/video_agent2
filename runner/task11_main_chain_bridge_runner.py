# -*- coding: utf-8 -*-
"""
runner/task11_main_chain_bridge_runner.py

【Task11：main_chain_bridge 最小安全执行器】

作用：
1. 读取 data/current/scene_assets_v2.json
2. 读取 data/current/scene_assets_preview.json
3. 转换为主链接入前的桥接结构
4. 生成 data/current/main_chain_bridge.json

边界：
- 不修改任何旧主链文件
- 不接入旧主链执行
- 仅作为桥接准备层
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



def build_preview_lookup(preview_items: List[Dict[str, Any]]) -> Dict[Any, Dict[str, Any]]:
    """为 preview items 建立 scene_id 索引"""
    lookup: Dict[Any, Dict[str, Any]] = {}

    for item in preview_items:
        scene_id = item.get("scene_id")
        if scene_id is not None and scene_id not in lookup:
            lookup[scene_id] = item

    return lookup



def find_preview_item(
    scene_asset_item: Dict[str, Any],
    scene_index: int,
    preview_lookup: Dict[Any, Dict[str, Any]],
    preview_items: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """按 scene_id 优先、按顺序兜底匹配 preview item"""
    scene_id = scene_asset_item.get("scene_id")
    if scene_id is not None and scene_id in preview_lookup:
        return preview_lookup[scene_id]

    if scene_index < len(preview_items):
        return preview_items[scene_index]

    return None



def extract_asset_path(assets: List[Dict[str, Any]], asset_type: str) -> str:
    """从 assets 数组中提取指定类型的路径"""
    for asset in assets:
        if isinstance(asset, dict) and asset.get("type") == asset_type:
            path = asset.get("path", "")
            if isinstance(path, str):
                return path
    return ""



def build_bridge_items(
    scene_assets_items: List[Dict[str, Any]],
    preview_items: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """构建桥接层 items"""
    items: List[Dict[str, Any]] = []
    preview_lookup = build_preview_lookup(preview_items)

    for index, scene_asset_item in enumerate(scene_assets_items):
        preview_item = find_preview_item(scene_asset_item, index, preview_lookup, preview_items) or {}
        assets = scene_asset_item.get("assets")
        if not isinstance(assets, list):
            assets = []

        asset_count = preview_item.get("asset_count")
        if not isinstance(asset_count, int):
            asset_count = len(assets)

        bridge_status = preview_item.get("status", "incomplete")
        if not isinstance(bridge_status, str):
            bridge_status = "incomplete"

        use_fallback = bool(preview_item.get("fallback", False))

        items.append(
            {
                "scene_id": scene_asset_item.get("scene_id"),
                "role": scene_asset_item.get("role", ""),
                "type": scene_asset_item.get("type", ""),
                "bridge_status": bridge_status,
                "use_fallback": use_fallback,
                "primary_asset_path": extract_asset_path(assets, "primary"),
                "secondary_asset_path": extract_asset_path(assets, "secondary"),
                "asset_count": asset_count,
            }
        )

    return items



def build_summary(bridge_items: List[Dict[str, Any]]) -> Dict[str, int]:
    """构建顶层统计字段"""
    ready_scene_count = 0
    fallback_scene_count = 0

    for item in bridge_items:
        if item.get("bridge_status") == "ready":
            ready_scene_count += 1
        if item.get("use_fallback"):
            fallback_scene_count += 1

    return {
        "scene_count": len(bridge_items),
        "ready_scene_count": ready_scene_count,
        "fallback_scene_count": fallback_scene_count,
    }



def main() -> None:
    """主执行入口"""
    scene_assets_file = PROJECT_ROOT / "data" / "current" / "scene_assets_v2.json"
    preview_file = PROJECT_ROOT / "data" / "current" / "scene_assets_preview.json"
    output_file = PROJECT_ROOT / "data" / "current" / "main_chain_bridge.json"

    print("=" * 60)
    print("开始执行 Task11：生成 main_chain_bridge.json")
    print("=" * 60)
    print(f"输入文件1：{scene_assets_file}")
    print(f"输入文件2：{preview_file}")
    print(f"输出文件：{output_file}")

    scene_assets_data = load_json(scene_assets_file)
    preview_data = load_json(preview_file)

    scene_assets_items = extract_items(scene_assets_data, "scene_assets_v2.json")
    preview_items = extract_items(preview_data, "scene_assets_preview.json")
    bridge_items = build_bridge_items(scene_assets_items, preview_items)
    summary = build_summary(bridge_items)

    output_data = {
        "source_scene_assets_file": "data/current/scene_assets_v2.json",
        "source_preview_file": "data/current/scene_assets_preview.json",
        "output_file": "data/current/main_chain_bridge.json",
        "scene_count": summary["scene_count"],
        "ready_scene_count": summary["ready_scene_count"],
        "fallback_scene_count": summary["fallback_scene_count"],
        "items": bridge_items,
    }

    save_json(output_file, output_data)

    print("✅ main_chain_bridge.json 已生成")
    print(f"输出路径：{output_file}")
    print(f"场景数量：{summary['scene_count']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
