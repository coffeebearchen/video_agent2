# -*- coding: utf-8 -*-
"""
modules/scene_decision_debugger.py

【作用】
1. 为每个 scene 构建标准化素材决策调试记录
2. 汇总为统一的调试输出结构
3. 保存到 data/current/scene_decision_debug.json

【边界】
- 只处理调试数据
- 不参与渲染
- 不依赖 moviepy
- 仅使用 Python 标准库
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules import project_paths


def build_scene_decision_record(
    scene_id: Any,
    scene_index: int,
    bridge_hit: bool,
    bridge_status: str,
    bridge_primary_path: str,
    bridge_secondary_path: str,
    old_logic_path: str,
    old_logic_type: str,
    fallback_path: str,
    final_selected_path: str,
    final_selected_type: str,
    decision_source: str,
    fallback_used: bool,
    status: str,
    reason: str,
) -> Dict[str, Any]:
    """构建单个 scene 的调试记录。"""
    return {
        "scene_id": scene_id,
        "scene_index": scene_index,
        "bridge_hit": bridge_hit,
        "bridge_status": bridge_status,
        "bridge_primary_path": bridge_primary_path,
        "bridge_secondary_path": bridge_secondary_path,
        "old_logic_path": old_logic_path,
        "old_logic_type": old_logic_type,
        "fallback_path": fallback_path,
        "final_selected_path": final_selected_path,
        "final_selected_type": final_selected_type,
        "decision_source": decision_source,
        "fallback_used": fallback_used,
        "status": status,
        "reason": reason,
    }


def build_scene_decision_debug_payload(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """构建调试输出顶层结构。"""
    return {
        "output_file": "data/current/scene_decision_debug.json",
        "scene_count": len(records),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "items": records,
    }


def save_scene_decision_debug(
    records: List[Dict[str, Any]],
    output_path: Optional[Path] = None,
) -> Path:
    """保存调试文件，返回输出路径。"""
    target_path = output_path or (project_paths.get_data_current_dir() / "scene_decision_debug.json")
    payload = build_scene_decision_debug_payload(records)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with target_path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    return target_path