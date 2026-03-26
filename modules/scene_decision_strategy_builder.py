# -*- coding: utf-8 -*-
"""
modules/scene_decision_strategy_builder.py

【作用】
1. 读取 scene_decision_feedback.json
2. 把逐 scene feedback 聚合为系统级策略建议
3. 生成统一 strategy payload
4. 保存到 data/current/scene_decision_strategy.json

【边界】
- 只做策略理解与排序
- 不修改任何现有决策结果
- 不依赖渲染主流程
- 仅使用 Python 标准库
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules import project_paths


ACTION_TO_STRATEGY = {
    "review_asset_availability": {
        "strategy_key": "asset_availability",
        "priority": "medium",
        "strategy_reason": "当前系统素材可用性不足，应优先补素材池或素材覆盖率",
        "recommended_next_step": "检查素材池覆盖率并补充缺失主题素材",
    },
    "add_minimum_visual_asset": {
        "strategy_key": "minimum_visual_guard",
        "priority": "high",
        "strategy_reason": "当前存在 scene 只能落到纯色底图，应优先建立最小视觉保底",
        "recommended_next_step": "为缺素材场景建立最小图卡或背景视觉保底",
    },
    "check_final_asset_path": {
        "strategy_key": "asset_path_integrity",
        "priority": "high",
        "strategy_reason": "当前路径完整性有问题，应优先检查路径生成与落盘一致性",
        "recommended_next_step": "核对素材路径生成、相对路径转换与文件落盘结果",
    },
    "improve_decision_trace": {
        "strategy_key": "trace_quality",
        "priority": "low",
        "strategy_reason": "当前解释链不完整，应优先补 trace / reason 记录质量",
        "recommended_next_step": "补齐决策 reason 与 trace 字段，增强可解释性",
    },
    "review_bridge_mapping": {
        "strategy_key": "bridge_mapping_quality",
        "priority": "low",
        "strategy_reason": "bridge 命中但未使用，说明 bridge 映射质量需要优先排查",
        "recommended_next_step": "核查 bridge scene_id 对齐和素材路径有效性",
    },
    "normalize_asset_type": {
        "strategy_key": "asset_type_normalization",
        "priority": "medium",
        "strategy_reason": "素材类型归一化不足，应优先统一 image/video/type 逻辑",
        "recommended_next_step": "统一素材类型命名和路径到类型推断规则",
    },
}

PRIORITY_WEIGHT = {
    "high": 3,
    "medium": 2,
    "low": 1,
}


def load_scene_decision_feedback(file_path: Optional[Path] = None) -> Dict[str, Any]:
    """读取 scene_decision_feedback.json。"""
    feedback_path = file_path or (project_paths.get_data_current_dir() / "scene_decision_feedback.json")

    if not feedback_path.exists() or not feedback_path.is_file():
        raise FileNotFoundError(f"scene_decision_feedback.json 不存在：{feedback_path}")

    with feedback_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("scene_decision_feedback.json 顶层必须是对象。")

    items = data.get("items")
    if not isinstance(items, list):
        raise ValueError("scene_decision_feedback.json 缺少有效的 items 列表。")

    return data


def aggregate_feedback_to_strategy(feedback_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """把 feedback items 聚合成 strategy_items。"""
    aggregated: Dict[str, Dict[str, Any]] = {}

    for item in feedback_items:
        if not isinstance(item, dict):
            continue

        scene_id = item.get("scene_id")
        suggested_actions = item.get("suggested_actions", [])
        if not isinstance(suggested_actions, list):
            continue

        for action in suggested_actions:
            config = ACTION_TO_STRATEGY.get(action)
            if config is None:
                continue

            strategy_key = config["strategy_key"]
            if strategy_key not in aggregated:
                aggregated[strategy_key] = {
                    "strategy_key": strategy_key,
                    "related_actions": [],
                    "hit_count": 0,
                    "affected_scene_ids": [],
                    "priority": config["priority"],
                    "strategy_reason": config["strategy_reason"],
                    "recommended_next_step": config["recommended_next_step"],
                }

            strategy_item = aggregated[strategy_key]
            strategy_item["hit_count"] += 1

            if action not in strategy_item["related_actions"]:
                strategy_item["related_actions"].append(action)

            if scene_id not in strategy_item["affected_scene_ids"]:
                strategy_item["affected_scene_ids"].append(scene_id)

    strategy_items = list(aggregated.values())
    strategy_items.sort(
        key=lambda item: (
            -PRIORITY_WEIGHT.get(str(item.get("priority", "low")), 0),
            -int(item.get("hit_count", 0)),
            str(item.get("strategy_key", "")),
        )
    )
    return strategy_items


def build_scene_decision_strategy_payload(feedback_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """生成顶层 strategy payload 和 summary。"""
    strategy_items = aggregate_feedback_to_strategy(feedback_items)

    total_feedback_count = 0
    affected_scene_ids = set()
    high_priority_scene_count = 0
    medium_priority_scene_count = 0
    low_priority_scene_count = 0

    for item in feedback_items:
        if not isinstance(item, dict):
            continue

        suggested_actions = item.get("suggested_actions", [])
        if isinstance(suggested_actions, list):
            total_feedback_count += len(suggested_actions)
            if suggested_actions:
                affected_scene_ids.add(item.get("scene_id"))

        priority = str(item.get("priority", "none") or "none")
        if priority == "high":
            high_priority_scene_count += 1
        elif priority == "medium":
            medium_priority_scene_count += 1
        elif priority == "low":
            low_priority_scene_count += 1

    recommended_priority_order = [item["strategy_key"] for item in strategy_items]
    dominant_strategy = strategy_items[0]["strategy_key"] if strategy_items else "none"

    return {
        "output_file": "data/current/scene_decision_strategy.json",
        "scene_count": len([item for item in feedback_items if isinstance(item, dict)]),
        "summary": {
            "total_feedback_count": total_feedback_count,
            "affected_scene_count": len(affected_scene_ids),
            "dominant_strategy": dominant_strategy,
            "high_priority_scene_count": high_priority_scene_count,
            "medium_priority_scene_count": medium_priority_scene_count,
            "low_priority_scene_count": low_priority_scene_count,
        },
        "strategy_items": strategy_items,
        "recommended_priority_order": recommended_priority_order,
    }


def save_scene_decision_strategy(
    payload: Dict[str, Any],
    output_path: Optional[Path] = None,
) -> Path:
    """保存 scene_decision_strategy.json。"""
    target_path = output_path or (project_paths.get_data_current_dir() / "scene_decision_strategy.json")
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with target_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    return target_path