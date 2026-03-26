# -*- coding: utf-8 -*-
"""
modules/scene_decision_manual_trigger_plan_builder.py

【作用】
1. 读取 scene_decision_human_execution_interface.json
2. 将 execution_items 转换为人工触发清单
3. 输出 scene_decision_manual_trigger_plan.json

【边界】
- 只做人工触发判断，不自动执行任何动作
- 不修改任何已有输入 JSON
- 不依赖渲染主流程
- 仅使用 Python 标准库
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules import project_paths


def load_scene_decision_human_execution_interface(
    file_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """读取 scene_decision_human_execution_interface.json。"""
    interface_path = file_path or (
        project_paths.get_data_current_dir() / "scene_decision_human_execution_interface.json"
    )

    if not interface_path.exists() or not interface_path.is_file():
        raise FileNotFoundError(
            f"scene_decision_human_execution_interface.json 不存在：{interface_path}"
        )

    with interface_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("scene_decision_human_execution_interface.json 顶层必须是对象。")

    execution_items = data.get("execution_items")
    if execution_items is None:
        data["execution_items"] = []
    elif not isinstance(execution_items, list):
        raise ValueError(
            "scene_decision_human_execution_interface.json 中 execution_items 必须是列表。"
        )

    return data


def resolve_triggerable(approval_status: str, execution_status: str) -> bool:
    """根据审批状态和执行状态判断是否允许人工触发。"""
    if approval_status != "approved":
        return False

    if execution_status in {"ready", "not_started"}:
        return True

    return False


def resolve_trigger_block_reason(approval_status: str, execution_status: str, triggerable: bool) -> str:
    """生成触发阻断原因。"""
    if triggerable:
        return "当前可人工触发"

    if approval_status == "pending":
        return "等待人工审批"
    if approval_status == "rejected":
        return "已被拒绝，禁止触发"
    if approval_status == "deferred":
        return "已延期，暂不触发"
    if execution_status == "completed":
        return "已完成，无需重复触发"
    if execution_status == "canceled":
        return "已取消，不可触发"

    return "当前不满足人工触发条件"


def resolve_recommended_trigger_step(
    approval_status: str,
    execution_status: str,
    action_type: str,
    operator_note: str,
    triggerable: bool,
) -> str:
    """生成建议的人工触发步骤。"""
    if triggerable:
        if operator_note.strip():
            return "人工确认当前备注无冲突后执行该动作"
        return "人工确认后执行该动作"

    if approval_status == "pending":
        if operator_note.strip():
            return "先审阅 operator_note，再决定是否审批通过"
        return "待审批通过后再触发"
    if approval_status == "rejected":
        return "当前无需操作，保持拒绝状态并记录原因"
    if approval_status == "deferred":
        return "延后处理，待条件满足后重新评估"
    if execution_status == "completed":
        return "当前无需操作，继续观察执行结果"
    if execution_status == "canceled":
        return "当前无需操作，保持取消状态"
    if action_type == "monitoring_only":
        return "当前无需操作，继续观察"

    return "先补充 operator_note 再确认执行"


def build_trigger_item(index: int, execution_item: Dict[str, Any]) -> Dict[str, Any]:
    """把 execution_item 转换为 trigger_item。"""
    approval_status = str(execution_item.get("approval_status", "pending") or "pending")
    execution_status = str(execution_item.get("execution_status", "not_started") or "not_started")
    action_type = str(execution_item.get("action_type", "monitoring_only") or "monitoring_only")
    operator_note = str(execution_item.get("operator_note", "") or "")
    triggerable = resolve_triggerable(approval_status, execution_status)

    return {
        "trigger_id": f"trigger_{index:03d}",
        "execution_id": str(execution_item.get("execution_id", "")),
        "action_id": str(execution_item.get("action_id", "")),
        "action_name": str(execution_item.get("action_name", "未命名动作")),
        "approval_status": approval_status,
        "execution_status": execution_status,
        "triggerable": triggerable,
        "trigger_block_reason": resolve_trigger_block_reason(
            approval_status,
            execution_status,
            triggerable,
        ),
        "manual_trigger_required": True,
        "recommended_trigger_step": resolve_recommended_trigger_step(
            approval_status,
            execution_status,
            action_type,
            operator_note,
            triggerable,
        ),
        "target_scope": str(execution_item.get("target_scope", "unknown")),
        "risk_level": str(execution_item.get("risk_level", "low") or "low"),
        "operator_note": operator_note,
    }


def build_manual_trigger_plan(interface_data: Dict[str, Any]) -> Dict[str, Any]:
    """汇总 trigger_items 并生成顶层人工触发清单。"""
    execution_items = interface_data.get("execution_items", [])
    trigger_items: List[Dict[str, Any]] = []

    for index, execution_item in enumerate(execution_items, start=1):
        if not isinstance(execution_item, dict):
            continue
        trigger_items.append(build_trigger_item(index, execution_item))

    triggerable_count = sum(1 for item in trigger_items if item.get("triggerable") is True)
    total_trigger_items = len(trigger_items)

    return {
        "output_file": "data/current/scene_decision_manual_trigger_plan.json",
        "scene_count": int(interface_data.get("scene_count", 0) or 0),
        "overall_status": str(interface_data.get("overall_status", "stable") or "stable"),
        "total_trigger_items": total_trigger_items,
        "triggerable_count": triggerable_count,
        "blocked_count": total_trigger_items - triggerable_count,
        "manual_only": True,
        "trigger_items": trigger_items,
    }


def save_scene_decision_manual_trigger_plan(
    payload: Dict[str, Any],
    output_path: Optional[Path] = None,
) -> Path:
    """保存 scene_decision_manual_trigger_plan.json。"""
    target_path = output_path or (
        project_paths.get_data_current_dir() / "scene_decision_manual_trigger_plan.json"
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with target_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    return target_path