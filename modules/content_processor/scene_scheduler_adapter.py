# -*- coding: utf-8 -*-
"""
正式 Scheduler Adapter V1。

职责：
1. 将 formal selected_assets_plan 整理为 scheduler_ready_plan
2. 只做 selected -> scheduler-ready 的结构适配与落盘
3. 不调用 scene_clip_scheduler
4. 不生成 timeline
5. 不做剪辑 / render / video assembly
6. 不替换旧视频主链，只为后续 scene_clip_scheduler 接入做准备
"""

from __future__ import annotations

import json
from pathlib import Path


DEFAULT_ADAPTER_MODE = "scheduler_adapter_v1"
DEFAULT_NEXT_EXPECTED_STAGE = "scene_clip_scheduler"
DEFAULT_DURATION_HINT = "short"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCHEDULER_READY_PLAN_PATH = PROJECT_ROOT / "data" / "current" / "scheduler_ready_plan.json"


def _normalize_string(value: object) -> str:
    return str(value or "").strip()


def _normalize_selected_scenes(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []

    results: list[dict] = []
    for item in value:
        if isinstance(item, dict):
            results.append(item)
    return results


def _normalize_asset(value: object) -> dict:
    return dict(value) if isinstance(value, dict) else {}


def _write_scheduler_ready_plan(scheduler_ready_plan: dict) -> None:
    SCHEDULER_READY_PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SCHEDULER_READY_PLAN_PATH.open("w", encoding="utf-8") as file:
        json.dump(scheduler_ready_plan, file, ensure_ascii=False, indent=2)


def _build_schedule_scene(selected_scene: dict, scene_index: int) -> dict:
    asset = _normalize_asset(selected_scene.get("selected_asset"))
    duration_hint = _normalize_string(asset.get("duration_estimate")) or DEFAULT_DURATION_HINT
    return {
        "schedule_scene_id": f"schedule_scene_{scene_index + 1:03d}",
        "scene_id": _normalize_string(selected_scene.get("scene_id")) or f"scene_{scene_index + 1:03d}",
        "order": scene_index + 1,
        "asset": asset,
        "duration_hint": duration_hint,
        "text": _normalize_string(selected_scene.get("text")),
        "trace": {
            "selected_scene_id": _normalize_string(selected_scene.get("selected_scene_id")) or f"sel_scene_{scene_index + 1:03d}",
            "candidate_scene_id": _normalize_string(selected_scene.get("candidate_scene_id")) or f"cand_scene_{scene_index + 1:03d}",
        },
        "scheduler_hints": {
            "ready_for_scheduler": True,
            "timeline_generated": False,
            "render_attached": False,
        },
    }


def build_scheduler_ready_plan(content_package: dict, selected_assets_plan: dict) -> dict:
    source_selected_assets_plan = selected_assets_plan if isinstance(selected_assets_plan, dict) else {}
    selected_scenes = _normalize_selected_scenes(source_selected_assets_plan.get("selected_scenes"))

    schedule_scenes = [
        _build_schedule_scene(selected_scene, scene_index)
        for scene_index, selected_scene in enumerate(selected_scenes)
    ]
    scheduler_ready_plan = {
        "adapter_mode": DEFAULT_ADAPTER_MODE,
        "schedule_scene_count": len(schedule_scenes),
        "schedule_scenes": schedule_scenes,
        "adapter_global_hints": {
            "next_expected_stage": DEFAULT_NEXT_EXPECTED_STAGE,
            "scheduler_attached": False,
            "timeline_generated": False,
            "render_attached": False,
        },
    }

    _write_scheduler_ready_plan(scheduler_ready_plan)

    print(f"[SCHEDULER_ADAPTER] adapter_mode={scheduler_ready_plan['adapter_mode']}")
    print(f"[SCHEDULER_ADAPTER] schedule_scene_count={len(schedule_scenes)}")
    print(f"[SCHEDULER_ADAPTER] next_expected_stage={DEFAULT_NEXT_EXPECTED_STAGE}")

    return scheduler_ready_plan