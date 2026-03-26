# -*- coding: utf-8 -*-
"""
modules/scene_decision_safe_patch_plan_builder.py

【作用】
1. 读取 scene_decision_execution_targets.json
2. 将 target_item 转换为 patch 草案结构
3. 输出 scene_decision_safe_patch_plan.json

【边界】
- 只做 patch 草案，不执行任何 patch
- 不修改任何已有输入 JSON
- 不依赖渲染主流程
- 仅使用 Python 标准库
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules import project_paths


TARGET_TO_PATCH_MAPPING = {
    "bridge_mapping": {
        "operation": "update",
        "proposed_value": "<待确认的新 bridge 素材路径>",
    },
    "decision_trace": {
        "operation": "update",
        "proposed_value": "<待补充的 reason 文本>",
    },
    "asset_path": {
        "operation": "update",
        "proposed_value": "<待确认的新 file 路径>",
    },
    "asset_type": {
        "operation": "update",
        "proposed_value": "<待统一的 type 值>",
    },
    "asset_pool": {
        "operation": "append",
        "proposed_value": "<待补充的新素材文件>",
    },
    "monitoring_only": {
        "operation": "monitor_only",
        "proposed_value": "none",
    },
    "unknown": {
        "operation": "create_placeholder",
        "proposed_value": "<待人工确认的修改内容>",
    },
}

CONFIDENCE_TO_RISK = {
    "high": "medium",
    "medium": "medium",
    "low": "low",
}


def load_execution_targets(file_path: Optional[Path] = None) -> Dict[str, Any]:
    """读取 scene_decision_execution_targets.json。"""
    target_path = file_path or (
        project_paths.get_data_current_dir() / "scene_decision_execution_targets.json"
    )

    if not target_path.exists() or not target_path.is_file():
        raise FileNotFoundError(f"scene_decision_execution_targets.json 不存在：{target_path}")

    with target_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("scene_decision_execution_targets.json 顶层必须是对象。")

    target_items = data.get("target_items")
    if target_items is None:
        data["target_items"] = []
    elif not isinstance(target_items, list):
        raise ValueError("scene_decision_execution_targets.json 中 target_items 必须是列表。")

    return data


def resolve_patch_mapping(target_type: str) -> Dict[str, str]:
    """根据 target_type 返回 patch 草案映射。"""
    return TARGET_TO_PATCH_MAPPING.get(target_type, TARGET_TO_PATCH_MAPPING["unknown"])


def resolve_patch_risk_level(confidence: str) -> str:
    """根据 target 置信度映射 patch 风险等级。"""
    return CONFIDENCE_TO_RISK.get(confidence, "low")


def build_patch_item(index: int, target_item: Dict[str, Any]) -> Dict[str, Any]:
    """把 target_item 转换为 patch_item。"""
    target_type = str(target_item.get("target_type", "unknown") or "unknown")
    mapping = resolve_patch_mapping(target_type)
    target_file = str(target_item.get("target_file_candidate", "none") or "none")
    target_path = str(target_item.get("target_field_candidate", "none") or "none")
    confidence = str(target_item.get("target_resolution_confidence", "low") or "low")
    patch_reason = (
        f"基于 target 解析结果生成草案。"
        f" {str(target_item.get('resolution_reason', '') or '').strip()}"
    ).strip()

    return {
        "patch_id": f"patch_{index:03d}",
        "target_id": str(target_item.get("target_id", "")),
        "action_id": str(target_item.get("action_id", "")),
        "patch_status": "draft",
        "target_file": target_file,
        "operation": mapping["operation"],
        "target_path": target_path,
        "proposed_value": mapping["proposed_value"],
        "patch_reason": patch_reason,
        "patch_risk_level": resolve_patch_risk_level(confidence),
        "requires_human_review": True,
    }


def build_safe_patch_plan(targets_data: Dict[str, Any]) -> Dict[str, Any]:
    """生成顶层 safe patch plan 结构。"""
    target_items = targets_data.get("target_items", [])
    patch_items: List[Dict[str, Any]] = []

    for index, target_item in enumerate(target_items, start=1):
        if not isinstance(target_item, dict):
            continue
        patch_items.append(build_patch_item(index, target_item))

    summary = {
        "draft_count": sum(1 for item in patch_items if item.get("patch_status") == "draft"),
        "update_count": sum(1 for item in patch_items if item.get("operation") == "update"),
        "append_count": sum(1 for item in patch_items if item.get("operation") == "append"),
        "monitor_only_count": sum(1 for item in patch_items if item.get("operation") == "monitor_only"),
        "requires_human_review_count": sum(1 for item in patch_items if item.get("requires_human_review") is True),
    }

    return {
        "output_file": "data/current/scene_decision_safe_patch_plan.json",
        "scene_count": int(targets_data.get("scene_count", 0) or 0),
        "total_patch_items": len(patch_items),
        "summary": summary,
        "patch_items": patch_items,
    }


def save_safe_patch_plan(
    payload: Dict[str, Any],
    output_path: Optional[Path] = None,
) -> Path:
    """保存 scene_decision_safe_patch_plan.json。"""
    target_path = output_path or (
        project_paths.get_data_current_dir() / "scene_decision_safe_patch_plan.json"
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with target_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    return target_path