# -*- coding: utf-8 -*-
"""
Scheduler integration adapter for isolated M4 verification.

职责：
1. 将 scheduler_ready_plan 转换为 scene_clip_scheduler 可消费的最小输入结构
2. 仅做结构适配，不进入 timeline / render / video execution
"""

from __future__ import annotations


DEFAULT_DURATION = "short"


def _normalize_string(value: object) -> str:
    return str(value or "").strip()


def _normalize_schedule_scenes(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []

    results: list[dict] = []
    for item in value:
        if isinstance(item, dict):
            results.append(item)
    return results


def _normalize_asset(value: object) -> dict:
    return dict(value) if isinstance(value, dict) else {}


def _build_scheduler_asset(asset: dict, scene_index: int) -> dict:
    normalized_asset = _normalize_asset(asset)
    candidate_id = _normalize_string(normalized_asset.get("candidate_id")) or f"sched_asset_{scene_index + 1:03d}"
    asset_type = _normalize_string(normalized_asset.get("type")) or "generated_stub"
    description = _normalize_string(normalized_asset.get("description"))
    source = _normalize_string(normalized_asset.get("source")) or "immediate"
    return {
        "asset_id": candidate_id,
        "asset_type": asset_type,
        "file_name": description,
        "url": "",
        "source": source,
        "duration_estimate": _normalize_string(normalized_asset.get("duration_estimate")) or DEFAULT_DURATION,
    }


def build_scheduler_input_plan(scheduler_ready_plan: dict) -> dict:
    source_plan = scheduler_ready_plan if isinstance(scheduler_ready_plan, dict) else {}
    schedule_scenes = _normalize_schedule_scenes(source_plan.get("schedule_scenes"))

    scenes = []
    for scene_index, schedule_scene in enumerate(schedule_scenes):
        scheduler_asset = _build_scheduler_asset(schedule_scene.get("asset"), scene_index)
        duration = (
            _normalize_string(schedule_scene.get("asset", {}).get("duration_estimate"))
            or _normalize_string(schedule_scene.get("duration_hint"))
            or DEFAULT_DURATION
        )
        scenes.append(
            {
                "scene_id": _normalize_string(schedule_scene.get("scene_id")) or f"scene_{scene_index + 1:03d}",
                "assets": [scheduler_asset],
                "duration": duration,
                "text": _normalize_string(schedule_scene.get("text")),
            }
        )

    return {"scenes": scenes}