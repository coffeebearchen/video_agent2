# -*- coding: utf-8 -*-
"""
runner/task10_scene_assets_preview_runner.py

【Task10：scene_assets_v2 预览检查器】

作用：
1. 读取 data/current/scene_assets_v2.json
2. 检查每个 scene 的 assets 结构是否完整
3. 统计 primary / secondary / fallback 情况
4. 生成 data/current/scene_assets_preview.json

边界：
- 不修改任何旧主链文件
- 不修改 scene_assets_v2.json
- 仅作为接主链前的安全检查层
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
    """从 scene_assets_v2.json 中提取 items 列表"""
    if isinstance(data, dict):
        items = data.get("items")
        if isinstance(items, list):
            return items

    raise ValueError("❌ scene_assets_v2.json 中未找到有效的 items 结构")



def has_asset_type(assets: List[Dict[str, Any]], asset_type: str) -> bool:
    """检查 assets 数组中是否存在指定类型的素材"""
    for asset in assets:
        if isinstance(asset, dict) and asset.get("type") == asset_type:
            return True
    return False



def resolve_status(fallback: bool, has_primary: bool) -> str:
    """根据规则计算状态"""
    if fallback:
        return "fallback"
    if has_primary:
        return "ready"
    return "incomplete"



def build_preview_items(scene_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """构建预览检查结果列表"""
    preview_items: List[Dict[str, Any]] = []

    for item in scene_items:
        assets = item.get("assets")
        if not isinstance(assets, list):
            assets = []

        fallback = bool(item.get("fallback", False))
        has_primary = has_asset_type(assets, "primary")
        has_secondary = has_asset_type(assets, "secondary")
        asset_count = len(assets)
        status = resolve_status(fallback, has_primary)

        preview_items.append(
            {
                "scene_id": item.get("scene_id"),
                "role": item.get("role", ""),
                "type": item.get("type", ""),
                "has_primary": has_primary,
                "has_secondary": has_secondary,
                "fallback": fallback,
                "asset_count": asset_count,
                "status": status,
            }
        )

    return preview_items



def build_summary(preview_items: List[Dict[str, Any]]) -> Dict[str, int]:
    """构建 summary 统计信息"""
    resolved_scene_count = 0
    fallback_scene_count = 0
    primary_asset_count = 0
    secondary_asset_count = 0

    for item in preview_items:
        if item.get("status") == "ready":
            resolved_scene_count += 1
        if item.get("fallback"):
            fallback_scene_count += 1
        if item.get("has_primary"):
            primary_asset_count += 1
        if item.get("has_secondary"):
            secondary_asset_count += 1

    return {
        "resolved_scene_count": resolved_scene_count,
        "fallback_scene_count": fallback_scene_count,
        "primary_asset_count": primary_asset_count,
        "secondary_asset_count": secondary_asset_count,
    }



def main() -> None:
    """主执行入口"""
    input_file = PROJECT_ROOT / "data" / "current" / "scene_assets_v2.json"
    output_file = PROJECT_ROOT / "data" / "current" / "scene_assets_preview.json"

    print("=" * 60)
    print("开始执行 Task10：生成 scene_assets_preview.json")
    print("=" * 60)
    print(f"输入文件：{input_file}")
    print(f"输出文件：{output_file}")

    input_data = load_json(input_file)
    scene_items = extract_items(input_data)
    preview_items = build_preview_items(scene_items)
    summary = build_summary(preview_items)

    output_data = {
        "scene_count": len(preview_items),
        "summary": summary,
        "items": preview_items,
    }

    save_json(output_file, output_data)

    print("✅ scene_assets_preview.json 已生成")
    print(f"输出路径：{output_file}")
    print(f"场景数量：{len(preview_items)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
