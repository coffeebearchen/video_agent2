# -*- coding: utf-8 -*-
"""
modules/scene_decision_action_plan_builder.py

【作用】
1. 读取 scene_decision_strategy.json 或 scene_decision_strategy_review.json
2. 转换为可执行但不自动执行的 action_plan.json
3. 输出结构化执行指令模板，供人工或后续系统参考

【边界】
- 只生成执行计划，不自动执行
- 不修改任何现有 JSON 输入文件
- 不依赖渲染主流程
- 仅使用 Python 标准库
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules import project_paths


STRATEGY_TO_ACTION = {
    "asset_availability": {
        "action_type": "asset_improvement",
        "action_name": "补充素材可用性",
        "execution_hint": "为该主题补充至少3个素材（图片或视频），并检查覆盖率是否达到可用阈值。",
        "expected_result": "fallback 使用率下降",
        "default_target_scope": "system_assets",
    },
    "minimum_visual_guard": {
        "action_type": "asset_improvement",
        "action_name": "建立最小视觉保底",
        "execution_hint": "为缺素材场景补充最小可用图卡、背景图或默认视频素材。",
        "expected_result": "渲染稳定性提升",
        "default_target_scope": "fallback_scenes",
    },
    "asset_path_integrity": {
        "action_type": "path_validation",
        "action_name": "校验素材路径完整性",
        "execution_hint": "校验素材路径是否存在文件，并检查路径生成、相对路径转换与文件落盘是否一致。",
        "expected_result": "渲染稳定性提升",
        "default_target_scope": "asset_paths",
    },
    "trace_quality": {
        "action_type": "trace_enhancement",
        "action_name": "增强决策链路记录",
        "execution_hint": "为决策链补充 reason 字段，并检查 trace 记录是否覆盖关键分支。",
        "expected_result": "debug trace 完整性提升",
        "default_target_scope": "decision_trace",
    },
    "bridge_mapping_quality": {
        "action_type": "bridge_fix",
        "action_name": "排查 bridge 映射质量",
        "execution_hint": "检查 bridge 映射规则是否正确命中，并核对 scene_id 与素材路径是否一致。",
        "expected_result": "bridge 命中率提升",
        "default_target_scope": "bridge_mapping",
    },
    "asset_type_normalization": {
        "action_type": "type_normalization",
        "action_name": "统一素材类型归一化",
        "execution_hint": "统一 image/video 类型标记与推断逻辑，并复核边界文件类型。",
        "expected_result": "素材类型判断一致性提升",
        "default_target_scope": "asset_types",
    },
    "none": {
        "action_type": "monitoring_only",
        "action_name": "维持观察",
        "execution_hint": "当前无需执行额外修复动作，维持例行观察并保留现有检查流程。",
        "expected_result": "保持当前稳定状态",
        "default_target_scope": "system_monitoring",
    },
}

ACTION_RISK_LEVEL = {
    "monitoring_only": "low",
    "trace_enhancement": "low",
    "asset_improvement": "medium",
    "bridge_fix": "medium",
    "type_normalization": "medium",
    "path_validation": "high",
}


def load_json_file(file_path: Path) -> Dict[str, Any]:
    """读取单个 JSON 文件。"""
    with file_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(f"JSON 顶层必须是对象：{file_path}")

    return data


def load_strategy_or_review(
    strategy_path: Optional[Path] = None,
    review_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """读取 strategy / review，并返回规范化输入。"""
    resolved_strategy_path = strategy_path or (project_paths.get_data_current_dir() / "scene_decision_strategy.json")
    resolved_review_path = review_path or (project_paths.get_data_current_dir() / "scene_decision_strategy_review.json")

    strategy_data: Optional[Dict[str, Any]] = None
    review_data: Optional[Dict[str, Any]] = None

    if resolved_strategy_path.exists() and resolved_strategy_path.is_file():
        strategy_data = load_json_file(resolved_strategy_path)

    if resolved_review_path.exists() and resolved_review_path.is_file():
        review_data = load_json_file(resolved_review_path)

    if strategy_data is None and review_data is None:
        raise FileNotFoundError(
            "未找到 scene_decision_strategy.json 或 scene_decision_strategy_review.json。"
        )

    return {
        "strategy": strategy_data,
        "review": review_data,
        "strategy_path": resolved_strategy_path,
        "review_path": resolved_review_path,
    }


def resolve_risk_level(action_type: str) -> str:
    """根据 action_type 返回风险等级。"""
    return ACTION_RISK_LEVEL.get(action_type, "medium")


def build_action_item(
    action_id: int,
    strategy_key: str,
    priority: str,
    affected_scene_ids: List[Any],
) -> Dict[str, Any]:
    """为单个策略构建 action_item。"""
    config = STRATEGY_TO_ACTION.get(strategy_key, STRATEGY_TO_ACTION["none"])
    action_type = str(config["action_type"])

    if strategy_key == "none":
        target_scope = config["default_target_scope"]
    elif affected_scene_ids:
        target_scope = f"scenes:{affected_scene_ids}"
    else:
        target_scope = config["default_target_scope"]

    return {
        "action_id": f"action_{action_id:03d}",
        "action_type": action_type,
        "action_name": config["action_name"],
        "related_strategy": strategy_key,
        "priority": priority,
        "target_scope": target_scope,
        "execution_hint": config["execution_hint"],
        "expected_result": config["expected_result"],
        "risk_level": resolve_risk_level(action_type),
    }


def build_action_plan(loaded_input: Dict[str, Any]) -> Dict[str, Any]:
    """把 strategy / review 转换为 action_plan。"""
    strategy_data = loaded_input.get("strategy") or {}
    review_data = loaded_input.get("review") or {}

    scene_count = int(
        review_data.get("scene_count")
        or strategy_data.get("scene_count")
        or 0
    )
    overall_status = str(
        review_data.get("overall_status")
        or "stable"
    )

    strategy_items = strategy_data.get("strategy_items")
    if not isinstance(strategy_items, list):
        strategy_items = []

    action_items: List[Dict[str, Any]] = []

    for index, item in enumerate(strategy_items, start=1):
        if not isinstance(item, dict):
            continue

        strategy_key = str(item.get("strategy_key", "none") or "none")
        priority = str(item.get("priority", "none") or "none")
        affected_scene_ids = item.get("affected_scene_ids", [])
        if not isinstance(affected_scene_ids, list):
            affected_scene_ids = []

        action_items.append(
            build_action_item(index, strategy_key, priority, affected_scene_ids)
        )

    if not action_items:
        dominant_strategy = str(
            review_data.get("dominant_strategy")
            or strategy_data.get("summary", {}).get("dominant_strategy")
            or "none"
        )
        action_items.append(
            build_action_item(
                action_id=1,
                strategy_key=dominant_strategy if dominant_strategy in STRATEGY_TO_ACTION else "none",
                priority="low",
                affected_scene_ids=[],
            )
        )

    return {
        "output_file": "data/current/scene_decision_action_plan.json",
        "scene_count": scene_count,
        "overall_status": overall_status,
        "action_items": action_items,
    }


def save_action_plan(
    payload: Dict[str, Any],
    output_path: Optional[Path] = None,
) -> Path:
    """保存 action_plan.json。"""
    target_path = output_path or (project_paths.get_data_current_dir() / "scene_decision_action_plan.json")
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with target_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    return target_path