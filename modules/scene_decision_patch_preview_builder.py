# -*- coding: utf-8 -*-
"""
modules/scene_decision_patch_preview_builder.py

【作用】
1. 读取 scene_assets.json 和 scene_decision_safe_patch_plan.json
2. 在内存中应用 patch 草案
3. 输出 patch 前后差异预览 JSON

【边界】
- 不修改任何输入文件
- 不依赖渲染主流程
- 仅使用 Python 标准库
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from modules import project_paths
from modules.scene_decision_patch_applier import (
    apply_patch_plan_to_scene_assets,
    load_patch_plan,
)


TRACKED_FIELDS = ["type", "file", "asset_type", "asset_file"]


def load_scene_assets(file_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """读取 scene_assets.json，兼容 list 和 {scene_assets: [...]} 两种格式。"""
    scene_assets_path = file_path or (project_paths.get_data_current_dir() / "scene_assets.json")

    if not scene_assets_path.exists() or not scene_assets_path.is_file():
        raise FileNotFoundError(f"scene_assets.json 不存在：{scene_assets_path}")

    with scene_assets_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, list):
        return data
    if isinstance(data, dict) and isinstance(data.get("scene_assets"), list):
        return data["scene_assets"]

    raise ValueError("scene_assets.json 格式错误，应为 list 或 {'scene_assets': [...]}。")


def load_preview_inputs(
    scene_assets_path: Optional[Path] = None,
    patch_plan_path: Optional[Path] = None,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """读取 preview 所需输入。"""
    scene_assets = load_scene_assets(scene_assets_path)
    patch_plan = load_patch_plan(patch_plan_path)

    if not isinstance(patch_plan, dict):
        raise FileNotFoundError("scene_decision_safe_patch_plan.json 不存在或格式无效。")

    patch_items = patch_plan.get("patch_items")
    if not isinstance(patch_items, list):
        raise ValueError("scene_decision_safe_patch_plan.json 中 patch_items 必须是列表。")

    return scene_assets, patch_plan


def resolve_related_patch_id(
    patch_items: List[Dict[str, Any]],
    field_name: str,
) -> str:
    """根据字段名推断最相关的 patch_id。"""
    for patch_item in patch_items:
        if not isinstance(patch_item, dict):
            continue

        target_path = str(patch_item.get("target_path", "none") or "none")
        target_file = str(patch_item.get("target_file", "none") or "none").replace("\\", "/").lower()
        operation = str(patch_item.get("operation", "monitor_only") or "monitor_only")

        if operation == "monitor_only":
            continue
        if "scene_assets.json" not in target_file:
            continue
        if target_path == field_name:
            return str(patch_item.get("patch_id", ""))

    return ""


def build_diff_items(
    original_scene_assets: List[Dict[str, Any]],
    patched_scene_assets: List[Dict[str, Any]],
    patch_items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """构建逐字段 diff 结果。"""
    diff_items: List[Dict[str, Any]] = []
    diff_index = 1
    max_len = max(len(original_scene_assets), len(patched_scene_assets))

    for scene_index in range(max_len):
        before_item = original_scene_assets[scene_index] if scene_index < len(original_scene_assets) else {}
        after_item = patched_scene_assets[scene_index] if scene_index < len(patched_scene_assets) else {}

        if not isinstance(before_item, dict):
            before_item = {}
        if not isinstance(after_item, dict):
            after_item = {}

        for field_name in TRACKED_FIELDS:
            before_value = before_item.get(field_name)
            after_value = after_item.get(field_name)
            changed = before_value != after_value

            if not changed:
                continue

            related_patch_id = resolve_related_patch_id(patch_items, field_name)
            diff_items.append(
                {
                    "diff_id": f"diff_{diff_index:03d}",
                    "scene_index": scene_index,
                    "field_name": field_name,
                    "before_value": before_value,
                    "after_value": after_value,
                    "changed": True,
                    "related_patch_id": related_patch_id,
                    "diff_reason": f"patch 草案导致字段 {field_name} 的内存值发生变化。",
                }
            )
            diff_index += 1

    return diff_items


def count_skipped_patches(
    patch_items: List[Dict[str, Any]],
    diff_items: List[Dict[str, Any]],
) -> int:
    """统计 monitor_only 或未生效 patch 数量。"""
    changed_patch_ids = {
        str(item.get("related_patch_id", ""))
        for item in diff_items
        if str(item.get("related_patch_id", ""))
    }

    skipped_count = 0
    for patch_item in patch_items:
        if not isinstance(patch_item, dict):
            continue

        patch_id = str(patch_item.get("patch_id", ""))
        operation = str(patch_item.get("operation", "monitor_only") or "monitor_only")
        if operation == "monitor_only":
            skipped_count += 1
            continue

        if patch_id not in changed_patch_ids:
            skipped_count += 1

    return skipped_count


def build_patch_preview(
    original_scene_assets: List[Dict[str, Any]],
    patch_plan: Dict[str, Any],
) -> Dict[str, Any]:
    """生成顶层 patch preview 结构。"""
    patch_items = patch_plan.get("patch_items", [])
    patched_scene_assets = apply_patch_plan_to_scene_assets(original_scene_assets, patch_plan)
    diff_items = build_diff_items(original_scene_assets, patched_scene_assets, patch_items)

    return {
        "output_file": "data/current/scene_decision_patch_preview.json",
        "original_scene_assets_count": len(original_scene_assets),
        "patched_scene_assets_count": len(patched_scene_assets),
        "patch_item_count": len([item for item in patch_items if isinstance(item, dict)]),
        "changed_item_count": len(diff_items),
        "skipped_patch_count": count_skipped_patches(patch_items, diff_items),
        "diff_items": diff_items,
    }


def save_patch_preview(
    payload: Dict[str, Any],
    output_path: Optional[Path] = None,
) -> Path:
    """保存 scene_decision_patch_preview.json。"""
    target_path = output_path or (
        project_paths.get_data_current_dir() / "scene_decision_patch_preview.json"
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with target_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    return target_path