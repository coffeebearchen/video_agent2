# -*- coding: utf-8 -*-
"""
modules/main_chain_bridge_loader.py

【作用】
1. 读取 data/current/main_chain_bridge.json
2. 做最小结构校验
3. 建立 scene_id -> bridge item 的安全索引
4. 为旧主链提供只读 bridge 查询能力

【边界】
- 只读 bridge 文件
- 不修改任何旧数据文件
- bridge 缺失或异常时返回安全空结果
- 仅使用 Python 标准库
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from modules import project_paths


def load_main_chain_bridge(file_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """
    读取 bridge JSON。

    返回：
    - 成功时返回 dict
    - 缺失、结构异常或读取异常时返回 None
    """
    bridge_path = file_path or (project_paths.get_data_current_dir() / "main_chain_bridge.json")

    try:
        if not bridge_path.exists() or not bridge_path.is_file():
            return None

        with bridge_path.open("r", encoding="utf-8") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            return None

        items = data.get("items")
        if not isinstance(items, list):
            return None

        return data
    except Exception:
        return None


def build_bridge_lookup(bridge_data: Optional[Dict[str, Any]]) -> Dict[Any, Dict[str, Any]]:
    """
    根据 scene_id 建立桥接索引。
    无效项会被自动忽略。
    """
    lookup: Dict[Any, Dict[str, Any]] = {}

    if not isinstance(bridge_data, dict):
        return lookup

    items = bridge_data.get("items")
    if not isinstance(items, list):
        return lookup

    for item in items:
        if not isinstance(item, dict):
            continue

        scene_id = item.get("scene_id")
        if scene_id is None or scene_id in lookup:
            continue

        lookup[scene_id] = item

    return lookup


def get_bridge_assets_for_scene(
    bridge_lookup: Optional[Dict[Any, Dict[str, Any]]],
    scene_id: Any,
) -> Optional[Dict[str, Any]]:
    """
    读取单个 scene 的 bridge 素材信息。

    仅当以下条件同时满足时才返回可用结果：
    - bridge_status == "ready"
    - use_fallback 为 False
    - 至少存在一个非空素材路径
    """
    if not isinstance(bridge_lookup, dict):
        return None

    item = bridge_lookup.get(scene_id)
    if not isinstance(item, dict):
        return None

    bridge_status = item.get("bridge_status", "")
    use_fallback = bool(item.get("use_fallback", False))
    primary_asset_path = str(item.get("primary_asset_path", "") or "").strip()
    secondary_asset_path = str(item.get("secondary_asset_path", "") or "").strip()

    if bridge_status != "ready":
        return None

    if use_fallback:
        return None

    if not primary_asset_path and not secondary_asset_path:
        return None

    return {
        "primary_asset_path": primary_asset_path,
        "secondary_asset_path": secondary_asset_path,
        "bridge_status": bridge_status,
        "use_fallback": use_fallback,
    }