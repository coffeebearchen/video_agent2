# -*- coding: utf-8 -*-
"""
modules/scene_decision_execution_target_resolver.py

【作用】
1. 读取 action_plan / human_execution_interface / execution_log
2. 将每个 action 解析为候选修改目标
3. 输出 scene_decision_execution_targets.json

【边界】
- 只做目标解析，不生成 patch，不执行任何动作
- 不修改任何已有输入 JSON
- 不依赖渲染主流程
- 仅使用 Python 标准库
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules import project_paths


ACTION_TARGET_MAPPING = {
    "asset_improvement": {
        "target_type": "asset_pool",
        "target_scope": "system_assets",
        "target_file_candidate": "assets/",
        "target_field_candidate": "none",
        "target_resolution_confidence": "medium",
        "resolution_reason": "该动作主要通过补充素材池改善覆盖率，通常不落在单一字段修改。",
    },
    "bridge_fix": {
        "target_type": "bridge_mapping",
        "target_scope": "bridge_layer",
        "target_file_candidate": "data/current/main_chain_bridge.json",
        "target_field_candidate": "items[].primary_asset_path / items[].secondary_asset_path",
        "target_resolution_confidence": "high",
        "resolution_reason": "该动作直接针对 bridge 映射层，主要候选目标是主桥接文件中的素材路径字段。",
    },
    "trace_enhancement": {
        "target_type": "decision_trace",
        "target_scope": "trace_layer",
        "target_file_candidate": "data/current/scene_decision_debug.json",
        "target_field_candidate": "reason",
        "target_resolution_confidence": "high",
        "resolution_reason": "该动作面向决策解释链，最可能补充的是 debug 记录中的 reason 字段。",
    },
    "path_validation": {
        "target_type": "asset_path",
        "target_scope": "asset_path_layer",
        "target_file_candidate": "data/current/scene_assets.json",
        "target_field_candidate": "file",
        "target_resolution_confidence": "medium",
        "resolution_reason": "该动作聚焦素材路径有效性，通常需要检查 scene 资产结构中的 file 字段。",
    },
    "type_normalization": {
        "target_type": "asset_type",
        "target_scope": "asset_type_layer",
        "target_file_candidate": "data/current/scene_assets.json",
        "target_field_candidate": "type",
        "target_resolution_confidence": "medium",
        "resolution_reason": "该动作聚焦素材类型统一，通常候选字段是资产结构中的 type 字段。",
    },
    "monitoring_only": {
        "target_type": "monitoring_only",
        "target_scope": "monitoring",
        "target_file_candidate": "none",
        "target_field_candidate": "none",
        "target_resolution_confidence": "low",
        "resolution_reason": "当前动作仅用于观察，不指向明确修改文件或字段。",
    },
}


def load_json_file(file_path: Path) -> Dict[str, Any]:
    """读取单个 JSON 文件。"""
    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError(f"输入文件不存在：{file_path}")

    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"JSON 顶层必须是对象：{file_path}")

    return data


def load_execution_target_inputs(
    action_plan_path: Optional[Path] = None,
    human_interface_path: Optional[Path] = None,
    execution_log_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """读取 target resolver 所需三层输入。"""
    data_current_dir = project_paths.get_data_current_dir()
    resolved_action_path = action_plan_path or (data_current_dir / "scene_decision_action_plan.json")
    resolved_human_path = human_interface_path or (data_current_dir / "scene_decision_human_execution_interface.json")
    resolved_log_path = execution_log_path or (data_current_dir / "scene_decision_execution_log.json")

    action_plan_data = load_json_file(resolved_action_path)
    human_interface_data = load_json_file(resolved_human_path)
    execution_log_data = load_json_file(resolved_log_path)

    if not isinstance(action_plan_data.get("action_items", []), list):
        raise ValueError("scene_decision_action_plan.json 中 action_items 必须是列表。")
    if not isinstance(human_interface_data.get("execution_items", []), list):
        raise ValueError("scene_decision_human_execution_interface.json 中 execution_items 必须是列表。")
    if not isinstance(execution_log_data.get("log_items", []), list):
        raise ValueError("scene_decision_execution_log.json 中 log_items 必须是列表。")

    return {
        "action_plan": action_plan_data,
        "human_interface": human_interface_data,
        "execution_log": execution_log_data,
    }


def build_target_item(
    index: int,
    action_item: Dict[str, Any],
    execution_item: Optional[Dict[str, Any]],
    log_item: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """根据 action 信息生成候选 target_item。"""
    action_type = str(action_item.get("action_type", "unknown") or "unknown")
    mapping = ACTION_TARGET_MAPPING.get(
        action_type,
        {
            "target_type": "unknown",
            "target_scope": "unknown",
            "target_file_candidate": "none",
            "target_field_candidate": "none",
            "target_resolution_confidence": "low",
            "resolution_reason": "当前动作类型缺少明确解析规则，暂只能给出低置信度候选目标。",
        },
    )

    resolution_reason = mapping["resolution_reason"]
    current_stage = str((log_item or {}).get("current_stage", "unknown") or "unknown")
    approval_status = str((execution_item or {}).get("approval_status", "pending") or "pending")
    if current_stage != "unknown":
        resolution_reason = f"{resolution_reason} 当前阶段为 {current_stage}，审批状态为 {approval_status}。"

    return {
        "target_id": f"target_{index:03d}",
        "action_id": str(action_item.get("action_id", "")),
        "action_name": str(action_item.get("action_name", "未命名动作") or "未命名动作"),
        "related_strategy": str(action_item.get("related_strategy", "none") or "none"),
        "target_type": mapping["target_type"],
        "target_scope": mapping["target_scope"],
        "target_file_candidate": mapping["target_file_candidate"],
        "target_field_candidate": mapping["target_field_candidate"],
        "target_resolution_confidence": mapping["target_resolution_confidence"],
        "resolution_reason": resolution_reason,
    }


def build_execution_targets(loaded_inputs: Dict[str, Any]) -> Dict[str, Any]:
    """生成顶层 execution targets 结构。"""
    action_plan_data = loaded_inputs["action_plan"]
    human_interface_data = loaded_inputs["human_interface"]
    execution_log_data = loaded_inputs["execution_log"]

    action_items = action_plan_data.get("action_items", [])
    execution_items = human_interface_data.get("execution_items", [])
    log_items = execution_log_data.get("log_items", [])

    execution_map = {
        str(item.get("action_id", "")): item
        for item in execution_items
        if isinstance(item, dict)
    }
    log_map = {
        str(item.get("action_id", "")): item
        for item in log_items
        if isinstance(item, dict)
    }

    target_items: List[Dict[str, Any]] = []
    for index, action_item in enumerate(action_items, start=1):
        if not isinstance(action_item, dict):
            continue

        action_id = str(action_item.get("action_id", ""))
        execution_item = execution_map.get(action_id)
        log_item = log_map.get(action_id)
        target_items.append(build_target_item(index, action_item, execution_item, log_item))

    target_type_counts: Dict[str, int] = {}
    for item in target_items:
        target_type = str(item.get("target_type", "unknown") or "unknown")
        target_type_counts[target_type] = target_type_counts.get(target_type, 0) + 1

    summary = {
        "high_confidence_count": sum(1 for item in target_items if item.get("target_resolution_confidence") == "high"),
        "medium_confidence_count": sum(1 for item in target_items if item.get("target_resolution_confidence") == "medium"),
        "low_confidence_count": sum(1 for item in target_items if item.get("target_resolution_confidence") == "low"),
        "target_type_counts": target_type_counts,
    }

    return {
        "output_file": "data/current/scene_decision_execution_targets.json",
        "scene_count": int(action_plan_data.get("scene_count", 0) or 0),
        "total_target_items": len(target_items),
        "summary": summary,
        "target_items": target_items,
    }


def save_execution_targets(
    payload: Dict[str, Any],
    output_path: Optional[Path] = None,
) -> Path:
    """保存 scene_decision_execution_targets.json。"""
    target_path = output_path or (
        project_paths.get_data_current_dir() / "scene_decision_execution_targets.json"
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with target_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    return target_path