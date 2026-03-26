# -*- coding: utf-8 -*-
"""
modules/scene_decision_execution_log_builder.py

【作用】
1. 读取 human_execution_interface / manual_trigger_plan / dry_run_result
2. 将多层状态聚合为统一 execution_log
3. 输出 scene_decision_execution_log.json

【边界】
- 只做日志聚合，不执行任何真实动作
- 不修改任何已有输入 JSON
- 不依赖渲染主流程
- 仅使用 Python 标准库
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules import project_paths


def load_json_file(file_path: Path) -> Dict[str, Any]:
    """读取单个 JSON 文件。"""
    if not file_path.exists() or not file_path.is_file():
        raise FileNotFoundError(f"输入文件不存在：{file_path}")

    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"JSON 顶层必须是对象：{file_path}")

    return data


def load_execution_layer_inputs(
    human_interface_path: Optional[Path] = None,
    manual_trigger_path: Optional[Path] = None,
    dry_run_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """读取 execution log 需要的三层输入。"""
    data_current_dir = project_paths.get_data_current_dir()
    resolved_human_path = human_interface_path or (data_current_dir / "scene_decision_human_execution_interface.json")
    resolved_trigger_path = manual_trigger_path or (data_current_dir / "scene_decision_manual_trigger_plan.json")
    resolved_dry_run_path = dry_run_path or (data_current_dir / "scene_decision_dry_run_result.json")

    human_data = load_json_file(resolved_human_path)
    trigger_data = load_json_file(resolved_trigger_path)
    dry_run_data = load_json_file(resolved_dry_run_path)

    if not isinstance(human_data.get("execution_items", []), list):
        raise ValueError("scene_decision_human_execution_interface.json 中 execution_items 必须是列表。")
    if not isinstance(trigger_data.get("trigger_items", []), list):
        raise ValueError("scene_decision_manual_trigger_plan.json 中 trigger_items 必须是列表。")
    if not isinstance(dry_run_data.get("dry_run_items", []), list):
        raise ValueError("scene_decision_dry_run_result.json 中 dry_run_items 必须是列表。")

    return {
        "human_interface": human_data,
        "manual_trigger_plan": trigger_data,
        "dry_run_result": dry_run_data,
    }


def resolve_current_stage(
    approval_status: str,
    execution_status: str,
    triggerable: bool,
    simulated_execution: str,
) -> str:
    """根据多层状态判断当前阶段。"""
    if execution_status in {"completed", "canceled"}:
        return "completed_like_record"
    if approval_status == "pending":
        return "pending_approval"
    if triggerable and simulated_execution == "simulated":
        return "ready_to_trigger"
    if approval_status in {"rejected", "deferred"}:
        return "blocked"
    if simulated_execution == "skipped":
        return "dry_run_only"
    if not triggerable:
        return "blocked"
    return "dry_run_only"


def resolve_latest_status(current_stage: str) -> str:
    """把阶段映射为简洁中文状态。"""
    if current_stage == "pending_approval":
        return "等待人工审批"
    if current_stage == "ready_to_trigger":
        return "可人工触发，已完成 dry-run"
    if current_stage == "blocked":
        return "当前被阻断，未进入执行"
    if current_stage == "dry_run_only":
        return "当前仅完成 dry-run 记录"
    if current_stage == "completed_like_record":
        return "当前记录显示动作已结束"
    return "当前状态待人工复核"


def build_trace_summary(
    action_type: str,
    approval_status: str,
    triggerable: bool,
    simulated_execution: str,
    simulated_impact: str,
) -> str:
    """将多层状态压缩为一句 trace 摘要。"""
    if action_type == "monitoring_only":
        return f"当前为 monitoring_only，审批状态为 {approval_status}，系统保持观察，dry-run 为 {simulated_execution}。"

    trigger_text = "可触发" if triggerable else "不可触发"
    return (
        f"动作已登记，审批状态为 {approval_status}，当前 {trigger_text}，"
        f"dry-run 为 {simulated_execution}，预期影响为：{simulated_impact}。"
    )


def build_log_item(
    index: int,
    execution_item: Dict[str, Any],
    trigger_item: Optional[Dict[str, Any]],
    dry_run_item: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """把 execution / trigger / dry-run 合并为单个 log_item。"""
    approval_status = str(execution_item.get("approval_status", "pending") or "pending")
    execution_status = str(execution_item.get("execution_status", "not_started") or "not_started")
    triggerable = bool((trigger_item or {}).get("triggerable", False))
    simulated_execution = str((dry_run_item or {}).get("simulated_execution", "skipped") or "skipped")
    action_type = str(execution_item.get("action_type", "monitoring_only") or "monitoring_only")
    simulated_impact = str((dry_run_item or {}).get("simulated_impact", "暂无 dry-run 影响说明") or "暂无 dry-run 影响说明")
    current_stage = resolve_current_stage(
        approval_status,
        execution_status,
        triggerable,
        simulated_execution,
    )

    return {
        "log_id": f"log_{index:03d}",
        "action_id": str(execution_item.get("action_id", "")),
        "execution_id": str(execution_item.get("execution_id", "")),
        "trigger_id": str((trigger_item or {}).get("trigger_id", "")),
        "action_name": str(execution_item.get("action_name", "未命名动作") or "未命名动作"),
        "approval_status": approval_status,
        "execution_status": execution_status,
        "triggerable": triggerable,
        "simulated_execution": simulated_execution,
        "current_stage": current_stage,
        "latest_status": resolve_latest_status(current_stage),
        "trace_summary": build_trace_summary(
            action_type,
            approval_status,
            triggerable,
            simulated_execution,
            simulated_impact,
        ),
        "operator_note": str(execution_item.get("operator_note", "") or ""),
    }


def build_execution_log(loaded_inputs: Dict[str, Any]) -> Dict[str, Any]:
    """生成顶层 execution_log 结构。"""
    human_data = loaded_inputs["human_interface"]
    trigger_data = loaded_inputs["manual_trigger_plan"]
    dry_run_data = loaded_inputs["dry_run_result"]

    execution_items = human_data.get("execution_items", [])
    trigger_items = trigger_data.get("trigger_items", [])
    dry_run_items = dry_run_data.get("dry_run_items", [])

    trigger_map = {
        str(item.get("execution_id", "")): item
        for item in trigger_items
        if isinstance(item, dict)
    }
    dry_run_map = {
        str(item.get("trigger_id", "")): item
        for item in dry_run_items
        if isinstance(item, dict)
    }

    log_items: List[Dict[str, Any]] = []
    for index, execution_item in enumerate(execution_items, start=1):
        if not isinstance(execution_item, dict):
            continue

        execution_id = str(execution_item.get("execution_id", ""))
        trigger_item = trigger_map.get(execution_id)
        trigger_id = str((trigger_item or {}).get("trigger_id", ""))
        dry_run_item = dry_run_map.get(trigger_id)
        log_items.append(build_log_item(index, execution_item, trigger_item, dry_run_item))

    summary = {
        "pending_approval_count": sum(1 for item in log_items if item.get("current_stage") == "pending_approval"),
        "ready_to_trigger_count": sum(1 for item in log_items if item.get("current_stage") == "ready_to_trigger"),
        "blocked_count": sum(1 for item in log_items if item.get("current_stage") == "blocked"),
        "dry_run_only_count": sum(1 for item in log_items if item.get("current_stage") == "dry_run_only"),
    }

    return {
        "output_file": "data/current/scene_decision_execution_log.json",
        "scene_count": int(human_data.get("scene_count", 0) or 0),
        "total_log_items": len(log_items),
        "summary": summary,
        "log_items": log_items,
    }


def save_execution_log(
    payload: Dict[str, Any],
    output_path: Optional[Path] = None,
) -> Path:
    """保存 scene_decision_execution_log.json。"""
    target_path = output_path or (
        project_paths.get_data_current_dir() / "scene_decision_execution_log.json"
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with target_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    return target_path