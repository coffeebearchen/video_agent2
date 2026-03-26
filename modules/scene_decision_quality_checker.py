# -*- coding: utf-8 -*-
"""
modules/scene_decision_quality_checker.py

【作用】
1. 读取 scene_decision_debug.json
2. 对每个 scene 的素材决策做质量校验
3. 汇总为结构化质量报告
4. 保存到 data/current/scene_decision_quality.json

【边界】
- 只做审计与质量检查
- 不修改任何素材决策结果
- 不依赖渲染主流程
- 仅使用 Python 标准库
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules import project_paths


def load_scene_decision_debug(file_path: Optional[Path] = None) -> Dict[str, Any]:
    """读取 scene_decision_debug.json。"""
    debug_path = file_path or (project_paths.get_data_current_dir() / "scene_decision_debug.json")

    if not debug_path.exists() or not debug_path.is_file():
        raise FileNotFoundError(f"scene_decision_debug.json 不存在：{debug_path}")

    with debug_path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("scene_decision_debug.json 顶层必须是对象。")

    items = data.get("items")
    if not isinstance(items, list):
        raise ValueError("scene_decision_debug.json 缺少有效的 items 列表。")

    return data


def evaluate_scene_decision_quality(record: Dict[str, Any]) -> Dict[str, Any]:
    """对单个 scene record 生成质量检查结果。"""
    scene_id = record.get("scene_id")
    scene_index = record.get("scene_index")
    decision_source = str(record.get("decision_source", "") or "")
    final_selected_type = str(record.get("final_selected_type", "") or "")
    final_selected_path = str(record.get("final_selected_path", "") or "")
    bridge_hit = bool(record.get("bridge_hit", False))
    fallback_used = bool(record.get("fallback_used", False))
    reason = str(record.get("reason", "") or "")

    quality_flags: List[str] = []
    quality_reasons: List[str] = []

    if fallback_used or decision_source in {"fallback_image", "fallback_color"}:
        quality_flags.append("fallback_used")
        if decision_source == "fallback_color":
            quality_reasons.append("使用了 fallback 纯色底图")
        else:
            quality_reasons.append("使用了 fallback 图卡")

    if not final_selected_type:
        quality_flags.append("unknown_type")
        quality_reasons.append("最终素材类型为空")

    if final_selected_type == "color":
        quality_flags.append("color_only")
        quality_reasons.append("最终只落到纯色底图")

    if bridge_hit and decision_source not in {"bridge_primary", "bridge_secondary"}:
        quality_flags.append("bridge_not_used")
        quality_reasons.append("bridge 命中但未实际使用 bridge 素材")

    if not final_selected_path and final_selected_type != "color":
        quality_flags.append("missing_final_path")
        quality_reasons.append("最终素材路径为空")

    if not reason:
        quality_flags.append("missing_reason")
        quality_reasons.append("缺少 reason 字段")

    quality_status = "ok"
    if "missing_final_path" in quality_flags or "color_only" in quality_flags:
        quality_status = "error"
    elif any(flag in quality_flags for flag in {"fallback_used", "missing_reason", "unknown_type"}):
        quality_status = "warning"
    elif "bridge_not_used" in quality_flags:
        quality_status = "info"

    quality_reason = "；".join(quality_reasons) if quality_reasons else "素材决策质量正常"

    return {
        "scene_id": scene_id,
        "scene_index": scene_index,
        "decision_source": decision_source,
        "final_selected_type": final_selected_type,
        "quality_status": quality_status,
        "quality_flags": quality_flags,
        "quality_reason": quality_reason,
        "original_reason": reason,
    }


def build_scene_decision_quality_payload(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """汇总全部结果并生成质量报告。"""
    items = [evaluate_scene_decision_quality(record) for record in records if isinstance(record, dict)]

    summary = {
        "ok_count": 0,
        "info_count": 0,
        "warning_count": 0,
        "error_count": 0,
        "fallback_count": 0,
    }

    for item in items:
        status = item.get("quality_status")
        if status == "ok":
            summary["ok_count"] += 1
        elif status == "info":
            summary["info_count"] += 1
        elif status == "warning":
            summary["warning_count"] += 1
        elif status == "error":
            summary["error_count"] += 1

        flags = item.get("quality_flags", [])
        if isinstance(flags, list) and "fallback_used" in flags:
            summary["fallback_count"] += 1

    return {
        "output_file": "data/current/scene_decision_quality.json",
        "scene_count": len(items),
        "summary": summary,
        "items": items,
    }


def save_scene_decision_quality(
    payload: Dict[str, Any],
    output_path: Optional[Path] = None,
) -> Path:
    """保存 scene_decision_quality.json。"""
    target_path = output_path or (project_paths.get_data_current_dir() / "scene_decision_quality.json")
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with target_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    return target_path