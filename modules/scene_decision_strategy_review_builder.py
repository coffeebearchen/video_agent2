# -*- coding: utf-8 -*-
"""
modules/scene_decision_strategy_review_builder.py

【作用】
1. 读取 scene_decision_strategy.json
2. 将策略聚合结果转换为人工可读的复核报告
3. 生成 scene_decision_strategy_review.json

【边界】
- 只做报告层表达，不做自动修复
- 不改任何素材决策结果
- 不依赖渲染主流程
- 仅使用 Python 标准库
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules import project_paths


DOMINANT_STRATEGY_EXPLANATIONS = {
    "asset_availability": "当前主要问题集中在素材可用性，建议优先补充素材池和覆盖率。",
    "minimum_visual_guard": "当前主要问题集中在最小视觉保底，建议为缺素材场景建立基础可用视觉。",
    "asset_path_integrity": "当前主要问题集中在素材路径完整性，建议优先检查路径生成与文件落盘一致性。",
    "trace_quality": "当前主要问题集中在决策 trace 质量，建议补齐 reason 与 trace 记录链路。",
    "bridge_mapping_quality": "当前主要问题集中在 bridge 映射质量，建议优先排查映射规则与命中结果。",
    "asset_type_normalization": "当前主要问题集中在素材类型归一化，建议统一 image/video 类型判断逻辑。",
    "none": "当前未形成主导性策略问题。",
}

FOCUS_SUGGESTIONS = {
    "asset_availability": "优先补充素材池和覆盖率",
    "minimum_visual_guard": "建立最小视觉保底素材",
    "asset_path_integrity": "检查路径生成与落盘一致性",
    "trace_quality": "提升 reason / trace 记录完整性",
    "bridge_mapping_quality": "检查 bridge 映射规则与命中逻辑",
    "asset_type_normalization": "统一素材类型归一化逻辑",
}

PRIORITY_LABELS = {
    "high": "高优先级",
    "medium": "中优先级",
    "low": "低优先级",
    "none": "无优先级",
}


def load_scene_decision_strategy(file_path: Optional[Path] = None) -> Dict[str, Any]:
    """读取 scene_decision_strategy.json。"""
    strategy_path = file_path or (project_paths.get_data_current_dir() / "scene_decision_strategy.json")

    if not strategy_path.exists() or not strategy_path.is_file():
        raise FileNotFoundError(f"scene_decision_strategy.json 不存在：{strategy_path}")

    with strategy_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("scene_decision_strategy.json 顶层必须是对象。")

    strategy_items = data.get("strategy_items")
    if strategy_items is None:
        data["strategy_items"] = []
    elif not isinstance(strategy_items, list):
        raise ValueError("scene_decision_strategy.json 中 strategy_items 必须是列表。")

    return data


def resolve_overall_status(priority_summary: Dict[str, Any]) -> str:
    """根据优先级统计生成整体状态。"""
    high_count = int(priority_summary.get("high_priority_scene_count", 0) or 0)
    medium_count = int(priority_summary.get("medium_priority_scene_count", 0) or 0)

    if high_count > 0:
        return "needs_attention"
    if medium_count > 0:
        return "watch"
    return "stable"


def build_key_findings(strategy_data: Dict[str, Any], overall_status: str) -> List[str]:
    """生成关键结论列表。"""
    findings: List[str] = []
    summary = strategy_data.get("summary", {})
    dominant_strategy = str(summary.get("dominant_strategy", "none") or "none")
    affected_scene_count = int(summary.get("affected_scene_count", 0) or 0)
    strategy_items = strategy_data.get("strategy_items", [])

    if not strategy_items:
        findings.append("当前未发现需要优先处理的系统级策略问题")
    else:
        findings.append(f"当前共识别出 {len(strategy_items)} 个系统级策略方向")

    if dominant_strategy == "none":
        findings.append("当前未形成主导性策略问题")
    else:
        findings.append(DOMINANT_STRATEGY_EXPLANATIONS.get(dominant_strategy, "当前存在需要人工复核的主导策略问题"))

    if affected_scene_count > 0:
        findings.append(f"当前共有 {affected_scene_count} 个 scene 受到策略问题影响")
    else:
        findings.append("当前没有 scene 被标记为受策略问题影响")

    if overall_status == "needs_attention":
        findings.append("当前存在高优先级问题，建议优先人工复核")
    elif overall_status == "watch":
        findings.append("当前存在中优先级问题，建议持续观察并安排排查")
    else:
        findings.append("当前策略层状态稳定，可继续维持观察")

    return findings[:5]


def build_recommended_focus(strategy_data: Dict[str, Any]) -> List[str]:
    """生成下一轮推荐关注方向。"""
    recommended_focus: List[str] = []
    strategy_items = strategy_data.get("strategy_items", [])
    dominant_strategy = str(strategy_data.get("summary", {}).get("dominant_strategy", "none") or "none")

    for item in strategy_items:
        if not isinstance(item, dict):
            continue

        strategy_key = str(item.get("strategy_key", "") or "")
        focus_text = FOCUS_SUGGESTIONS.get(strategy_key)
        if focus_text and focus_text not in recommended_focus:
            recommended_focus.append(focus_text)

    if not recommended_focus and dominant_strategy in FOCUS_SUGGESTIONS:
        recommended_focus.append(FOCUS_SUGGESTIONS[dominant_strategy])

    if not recommended_focus:
        recommended_focus.append("当前无需额外策略干预，继续保持例行观察")

    return recommended_focus


def build_review_items(strategy_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """把 strategy_items 转为人工可读 review_items。"""
    review_items: List[Dict[str, Any]] = []

    for item in strategy_items:
        if not isinstance(item, dict):
            continue

        strategy_key = str(item.get("strategy_key", "unknown") or "unknown")
        priority = str(item.get("priority", "none") or "none")
        hit_count = int(item.get("hit_count", 0) or 0)
        affected_scene_ids = item.get("affected_scene_ids", [])
        if not isinstance(affected_scene_ids, list):
            affected_scene_ids = []

        strategy_reason = str(item.get("strategy_reason", "暂无策略原因说明") or "暂无策略原因说明")
        next_step_advice = str(item.get("recommended_next_step", "建议继续人工复核") or "建议继续人工复核")
        priority_label = PRIORITY_LABELS.get(priority, "未知优先级")

        review_summary = (
            f"{priority_label}策略“{strategy_key}”当前命中 {hit_count} 次，"
            f"影响场景 {affected_scene_ids if affected_scene_ids else '无'}。{strategy_reason}"
        )

        review_items.append(
            {
                "strategy_key": strategy_key,
                "priority": priority,
                "hit_count": hit_count,
                "affected_scene_ids": affected_scene_ids,
                "review_summary": review_summary,
                "next_step_advice": next_step_advice,
            }
        )

    return review_items


def build_strategy_review_payload(strategy_data: Dict[str, Any]) -> Dict[str, Any]:
    """把 strategy 数据转换为人工复核报告结构。"""
    summary = strategy_data.get("summary", {})
    priority_summary = {
        "high_priority_scene_count": int(summary.get("high_priority_scene_count", 0) or 0),
        "medium_priority_scene_count": int(summary.get("medium_priority_scene_count", 0) or 0),
        "low_priority_scene_count": int(summary.get("low_priority_scene_count", 0) or 0),
    }
    overall_status = resolve_overall_status(priority_summary)
    dominant_strategy = str(summary.get("dominant_strategy", "none") or "none")
    dominant_strategy_explanation = DOMINANT_STRATEGY_EXPLANATIONS.get(
        dominant_strategy,
        "当前存在需要人工复核的策略问题。",
    )
    review_items = build_review_items(strategy_data.get("strategy_items", []))

    return {
        "output_file": "data/current/scene_decision_strategy_review.json",
        "scene_count": int(strategy_data.get("scene_count", 0) or 0),
        "overall_status": overall_status,
        "key_findings": build_key_findings(strategy_data, overall_status),
        "priority_summary": priority_summary,
        "dominant_strategy": dominant_strategy,
        "dominant_strategy_explanation": dominant_strategy_explanation,
        "recommended_focus": build_recommended_focus(strategy_data),
        "review_items": review_items,
    }


def save_scene_decision_strategy_review(
    payload: Dict[str, Any],
    output_path: Optional[Path] = None,
) -> Path:
    """保存 scene_decision_strategy_review.json。"""
    target_path = output_path or (project_paths.get_data_current_dir() / "scene_decision_strategy_review.json")
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with target_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    return target_path