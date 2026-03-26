# -*- coding: utf-8 -*-
"""
modules/scene_decision_patch_applier.py

【作用】
1. 读取 scene_decision_safe_patch_plan.json
2. 在内存中把 patch 草案尝试应用到 scene_assets 副本
3. 返回新的 scene_assets，不修改原始数据

【边界】
- 仅作用于内存对象
- 不写回任何文件
- patch 失败时返回安全副本
- 仅使用 Python 标准库
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules import project_paths


def load_patch_plan(file_path: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """读取 scene_decision_safe_patch_plan.json，缺失时返回 None。"""
    patch_plan_path = file_path or (
        project_paths.get_data_current_dir() / "scene_decision_safe_patch_plan.json"
    )

    if not patch_plan_path.exists() or not patch_plan_path.is_file():
        return None

    with patch_plan_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        return None

    patch_items = data.get("patch_items")
    if not isinstance(patch_items, list):
        return None

    return data


def resolve_patch_items(patch_plan: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """安全提取 patch_items。"""
    if not isinstance(patch_plan, dict):
        return []

    patch_items = patch_plan.get("patch_items", [])
    if not isinstance(patch_items, list):
        return []

    return [item for item in patch_items if isinstance(item, dict)]


def safe_apply_single_patch(
    scene_assets_copy: List[Dict[str, Any]],
    patch_item: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """安全应用单个 patch 到 scene_assets 副本。"""
    operation = str(patch_item.get("operation", "monitor_only") or "monitor_only")
    patch_status = str(patch_item.get("patch_status", "draft") or "draft")
    target_file = str(patch_item.get("target_file", "none") or "none")
    target_path = str(patch_item.get("target_path", "none") or "none")
    proposed_value = patch_item.get("proposed_value")

    if patch_status != "draft":
        return scene_assets_copy

    if operation == "monitor_only":
        return scene_assets_copy

    if target_file == "none" or target_path == "none":
        return scene_assets_copy

    normalized_target_file = target_file.replace("\\", "/").lower()
    if "scene_assets.json" not in normalized_target_file:
        return scene_assets_copy

    if operation == "update":
        if target_path not in {"file", "type", "asset_file", "asset_type"}:
            return scene_assets_copy

        for item in scene_assets_copy:
            if not isinstance(item, dict):
                continue
            item[target_path] = proposed_value

        return scene_assets_copy

    if operation == "append":
        if not isinstance(proposed_value, dict):
            return scene_assets_copy
        scene_assets_copy.append(copy.deepcopy(proposed_value))
        return scene_assets_copy

    return scene_assets_copy


def apply_patch_plan(
    scene_assets: List[Dict[str, Any]],
    patch_plan: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """将 patch_plan 应用到 scene_assets 副本并返回新对象。"""
    scene_assets_copy = copy.deepcopy(scene_assets)

    if not isinstance(scene_assets_copy, list):
        return scene_assets_copy

    for patch_item in resolve_patch_items(patch_plan):
        try:
            scene_assets_copy = safe_apply_single_patch(scene_assets_copy, patch_item)
        except Exception:
            continue

    return scene_assets_copy


def apply_patch_plan_to_scene_assets(
    scene_assets: List[Dict[str, Any]],
    patch_plan: Optional[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """对外暴露的受控 patch 应用入口。"""
    return apply_patch_plan(scene_assets, patch_plan)