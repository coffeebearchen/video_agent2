# -*- coding: utf-8 -*-
"""
modules/scene_decision_feedback_builder.py

【作用】
1. 读取 scene_decision_quality.json
2. 把质量问题转换为结构化 feedback 建议
3. 汇总为统一反馈报告
4. 保存到 data/current/scene_decision_feedback.json

【边界】
- 只做反馈建议，不自动修复
- 不修改任何现有决策结果
- 不依赖渲染主流程
- 仅使用 Python 标准库
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules import project_paths


FLAG_TO_ACTION = {
    "fallback_used": ("review_asset_availability", "当前 scene 使用了 fallback，说明素材可用性不足", "asset"),
    "color_only": ("add_minimum_visual_asset", "当前 scene 最终只能落到纯色底图", "scene"),
    "missing_final_path": ("check_final_asset_path", "最终素材路径缺失", "asset"),
    "missing_reason": ("improve_decision_trace", "当前 scene 的 reason 缺失，解释链不完整", "trace"),
    "bridge_not_used": ("review_bridge_mapping", "bridge 命中但未实际使用 bridge 素材", "bridge"),
    "unknown_type": ("normalize_asset_type", "最终素材类型不明确", "asset"),
}


def load_scene_decision_quality(file_path: Optional[Path] = None) -> Dict[str, Any]:
    """读取 scene_decision_quality.json。"""
    quality_path = file_path or (project_paths.get_data_current_dir() / "scene_decision_quality.json")

    if not quality_path.exists() or not quality_path.is_file():
        raise FileNotFoundError(f"scene_decision_quality.json 不存在：{quality_path}")

    with quality_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("scene_decision_quality.json 顶层必须是对象。")

    items = data.get("items")
    if not isinstance(items, list):
        raise ValueError("scene_decision_quality.json 缺少有效的 items 列表。")

    return data


def resolve_priority(flags: List[str]) -> str:
    """根据 flags 计算优先级。"""
    if any(flag in flags for flag in {"color_only", "missing_final_path"}):
        return "high"
    if any(flag in flags for flag in {"fallback_used", "unknown_type"}):
        return "medium"
    if any(flag in flags for flag in {"missing_reason", "bridge_not_used"}):
        return "low"
    return "none"


def resolve_feedback_level(flags: List[str]) -> str:
    """根据 flags 粗略映射 feedback_level。"""
    if any(flag in flags for flag in {"color_only", "fallback_used"}):
        return "scene"
    if any(flag in flags for flag in {"missing_final_path", "unknown_type"}):
        return "asset"
    if "bridge_not_used" in flags:
        return "bridge"
    if "missing_reason" in flags:
        return "trace"
    return "scene"


def build_feedback_for_scene(quality_item: Dict[str, Any]) -> Dict[str, Any]:
    """对单个 quality item 生成 feedback item。"""
    scene_id = quality_item.get("scene_id")
    scene_index = quality_item.get("scene_index")
    quality_status = str(quality_item.get("quality_status", "ok") or "ok")
    original_quality_reason = str(quality_item.get("quality_reason", "") or "")
    quality_flags_raw = quality_item.get("quality_flags", [])
    quality_flags = quality_flags_raw if isinstance(quality_flags_raw, list) else []

    suggested_actions: List[str] = []
    feedback_reasons: List[str] = []

    for flag in quality_flags:
        action_info = FLAG_TO_ACTION.get(flag)
        if action_info is None:
            continue

        action_name, action_reason, _level = action_info
        suggested_actions.append(action_name)
        feedback_reasons.append(action_reason)

    priority = resolve_priority(quality_flags)
    feedback_level = resolve_feedback_level(quality_flags)
    feedback_reason = "；".join(feedback_reasons) if feedback_reasons else "当前 scene 无需额外反馈"

    return {
        "scene_id": scene_id,
        "scene_index": scene_index,
        "quality_status": quality_status,
        "quality_flags": quality_flags,
        "feedback_level": feedback_level,
        "priority": priority,
        "suggested_actions": suggested_actions,
        "feedback_reason": feedback_reason,
        "original_quality_reason": original_quality_reason,
    }


def build_scene_decision_feedback_payload(quality_items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """汇总全部 feedback，生成顶层输出结构。"""
    items = [build_feedback_for_scene(item) for item in quality_items if isinstance(item, dict)]

    summary = {
        "total_feedback_count": 0,
        "scene_with_feedback_count": 0,
        "high_priority_count": 0,
        "medium_priority_count": 0,
        "low_priority_count": 0,
    }

    for item in items:
        suggested_actions = item.get("suggested_actions", [])
        priority = item.get("priority")

        if isinstance(suggested_actions, list):
            summary["total_feedback_count"] += len(suggested_actions)
            if suggested_actions:
                summary["scene_with_feedback_count"] += 1

        if priority == "high":
            summary["high_priority_count"] += 1
        elif priority == "medium":
            summary["medium_priority_count"] += 1
        elif priority == "low":
            summary["low_priority_count"] += 1

    return {
        "output_file": "data/current/scene_decision_feedback.json",
        "scene_count": len(items),
        "summary": summary,
        "items": items,
    }


def save_scene_decision_feedback(
    payload: Dict[str, Any],
    output_path: Optional[Path] = None,
) -> Path:
    """保存 scene_decision_feedback.json。"""
    target_path = output_path or (project_paths.get_data_current_dir() / "scene_decision_feedback.json")
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with target_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    return target_path