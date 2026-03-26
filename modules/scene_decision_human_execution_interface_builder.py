# -*- coding: utf-8 -*-
"""
modules/scene_decision_human_execution_interface_builder.py

【作用】
1. 读取 scene_decision_action_plan.json
2. 将 action_plan 转换为人工执行接口结构
3. 输出 scene_decision_human_execution_interface.json

【边界】
- 只做人工执行接口，不自动执行任何动作
- 不修改任何已有输入 JSON
- 不依赖渲染主流程
- 仅使用 Python 标准库
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules import project_paths


def load_scene_decision_action_plan(file_path: Optional[Path] = None) -> Dict[str, Any]:
    """读取 scene_decision_action_plan.json。"""
    action_plan_path = file_path or (project_paths.get_data_current_dir() / "scene_decision_action_plan.json")

    if not action_plan_path.exists() or not action_plan_path.is_file():
        raise FileNotFoundError(f"scene_decision_action_plan.json 不存在：{action_plan_path}")

    with action_plan_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("scene_decision_action_plan.json 顶层必须是对象。")

    action_items = data.get("action_items")
    if action_items is None:
        data["action_items"] = []
    elif not isinstance(action_items, list):
        raise ValueError("scene_decision_action_plan.json 中 action_items 必须是列表。")

    return data


def build_execution_item(index: int, action_item: Dict[str, Any]) -> Dict[str, Any]:
    """把 action_item 转换为人工 execution_item。"""
    return {
        "execution_id": f"execution_{index:03d}",
        "action_id": str(action_item.get("action_id", "")),
        "action_type": str(action_item.get("action_type", "monitoring_only")),
        "action_name": str(action_item.get("action_name", "未命名动作")),
        "priority": str(action_item.get("priority", "low")),
        "risk_level": str(action_item.get("risk_level", "low")),
        "human_decision_required": True,
        "allowed_execution_mode": "manual_only",
        "approval_status": "pending",
        "execution_status": "not_started",
        "target_scope": str(action_item.get("target_scope", "unknown")),
        "execution_hint": str(action_item.get("execution_hint", "")),
        "expected_result": str(action_item.get("expected_result", "")),
        "operator_note": "",
    }


def build_human_execution_interface(action_plan_data: Dict[str, Any]) -> Dict[str, Any]:
    """把 action_plan 转换为人工执行接口层结构。"""
    action_items = action_plan_data.get("action_items", [])
    execution_items: List[Dict[str, Any]] = []

    for index, action_item in enumerate(action_items, start=1):
        if not isinstance(action_item, dict):
            continue
        execution_items.append(build_execution_item(index, action_item))

    return {
        "output_file": "data/current/scene_decision_human_execution_interface.json",
        "scene_count": int(action_plan_data.get("scene_count", 0) or 0),
        "overall_status": str(action_plan_data.get("overall_status", "stable") or "stable"),
        "total_execution_items": len(execution_items),
        "manual_only": True,
        "execution_items": execution_items,
    }


def save_scene_decision_human_execution_interface(
    payload: Dict[str, Any],
    output_path: Optional[Path] = None,
) -> Path:
    """保存 scene_decision_human_execution_interface.json。"""
    target_path = output_path or (
        project_paths.get_data_current_dir() / "scene_decision_human_execution_interface.json"
    )
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with target_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    return target_path