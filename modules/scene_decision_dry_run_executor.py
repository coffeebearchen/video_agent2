# -*- coding: utf-8 -*-
"""
modules/scene_decision_dry_run_executor.py

【作用】
1. 读取 scene_decision_manual_trigger_plan.json
2. 对 triggerable 项做安全 dry-run 模拟
3. 输出 scene_decision_dry_run_result.json

【边界】
- 只做模拟，不执行任何真实动作
- 不修改任何输入 JSON
- 不依赖渲染主流程
- 仅使用 Python 标准库
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules import project_paths


ACTION_IMPACT_MAP = {
    "asset_improvement": "素材覆盖率提升，fallback 减少",
    "bridge_fix": "bridge 命中率提升",
    "trace_enhancement": "debug 可解释性提升",
    "path_validation": "路径错误减少，渲染稳定性提升",
    "type_normalization": "素材类型判断一致性提升",
    "monitoring_only": "系统保持稳定，无需改动",
}

ACTION_IMPROVEMENT_MAP = {
    "asset_improvement": "fallback_rate ↓, asset_hit_rate ↑",
    "bridge_fix": "asset_hit_rate ↑",
    "trace_enhancement": "debug_trace_quality ↑",
    "path_validation": "render_stability ↑",
    "type_normalization": "asset_hit_rate ↑, render_stability ↑",
    "monitoring_only": "system_stability = keep",
}

ACTION_RISK_MAP = {
    "monitoring_only": "low",
    "trace_enhancement": "low",
    "asset_improvement": "medium",
    "bridge_fix": "medium",
    "type_normalization": "medium",
    "path_validation": "high",
}


def load_manual_trigger_plan(file_path: Optional[Path] = None) -> Dict[str, Any]:
    """读取 scene_decision_manual_trigger_plan.json。"""
    trigger_plan_path = file_path or (
        project_paths.get_data_current_dir() / "scene_decision_manual_trigger_plan.json"
    )

    if not trigger_plan_path.exists() or not trigger_plan_path.is_file():
        raise FileNotFoundError(
            f"scene_decision_manual_trigger_plan.json 不存在：{trigger_plan_path}"
        )

    with trigger_plan_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("scene_decision_manual_trigger_plan.json 顶层必须是对象。")

    trigger_items = data.get("trigger_items")
    if trigger_items is None:
        data["trigger_items"] = []
    elif not isinstance(trigger_items, list):
        raise ValueError("scene_decision_manual_trigger_plan.json 中 trigger_items 必须是列表。")

    return data


def build_dry_run_item(index: int, trigger_item: Dict[str, Any]) -> Dict[str, Any]:
    """将 trigger_item 转为 dry_run_item。"""
    action_name = str(trigger_item.get("action_name", "未命名动作") or "未命名动作")
    triggerable = bool(trigger_item.get("triggerable", False))
    action_type = str(trigger_item.get("action_type", "monitoring_only") or "monitoring_only")

    if triggerable:
        simulated_execution = "simulated"
        simulation_note = "该动作满足人工触发条件，本次仅进行结果模拟，不会真实执行。"
    else:
        simulated_execution = "skipped"
        simulation_note = "该动作当前不满足人工触发条件，因此仅记录跳过结果。"

    return {
        "dry_run_id": f"dry_run_{index:03d}",
        "trigger_id": str(trigger_item.get("trigger_id", "")),
        "action_name": action_name,
        "triggerable": triggerable,
        "simulated_execution": simulated_execution,
        "simulated_impact": ACTION_IMPACT_MAP.get(action_type, "系统状态可能改善，但本次仅做模拟"),
        "expected_improvement": ACTION_IMPROVEMENT_MAP.get(action_type, "system_quality ↑"),
        "risk_assessment": ACTION_RISK_MAP.get(action_type, str(trigger_item.get("risk_level", "medium") or "medium")),
        "simulation_note": simulation_note,
    }


def build_dry_run_result(trigger_plan_data: Dict[str, Any]) -> Dict[str, Any]:
    """汇总 dry_run_items 并生成顶层结果。"""
    trigger_items = trigger_plan_data.get("trigger_items", [])
    dry_run_items: List[Dict[str, Any]] = []

    for index, trigger_item in enumerate(trigger_items, start=1):
        if not isinstance(trigger_item, dict):
            continue
        dry_run_items.append(build_dry_run_item(index, trigger_item))

    total_simulated = sum(1 for item in dry_run_items if item.get("simulated_execution") == "simulated")
    total_skipped = sum(1 for item in dry_run_items if item.get("simulated_execution") == "skipped")

    return {
        "output_file": "data/current/scene_decision_dry_run_result.json",
        "scene_count": int(trigger_plan_data.get("scene_count", 0) or 0),
        "total_simulated": total_simulated,
        "total_skipped": total_skipped,
        "dry_run_items": dry_run_items,
    }


def save_dry_run_result(
    payload: Dict[str, Any],
    output_path: Optional[Path] = None,
) -> Path:
    """保存 scene_decision_dry_run_result.json。"""
    target_path = output_path or (
        project_paths.get_data_current_dir() / "scene_decision_dry_run_result.json"
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with target_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    return target_path