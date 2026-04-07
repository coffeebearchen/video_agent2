# -*- coding: utf-8 -*-
"""
Timeline builder for isolated M4 verification.

职责：
1. 将 scheduler_output 转换为 timeline_plan
2. 构建稳定、连续、可验证的时间结构
3. 不触发 render / video_engine
"""

from __future__ import annotations

import json
from pathlib import Path


DURATION_MAP = {
    "short": 3,
    "medium": 5,
    "long": 8,
}
DEFAULT_DURATION = 3
TIMELINE_PLAN_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "current" / "timeline_plan.json"


def _normalize_scenes(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []

    results: list[dict] = []
    for item in value:
        if isinstance(item, dict):
            results.append(item)
    return results


def _normalize_clips(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []

    results: list[dict] = []
    for item in value:
        if isinstance(item, dict):
            results.append(item)
    return results


def _normalize_asset(value: object) -> dict:
    return dict(value) if isinstance(value, dict) else {}


def _normalize_string(value: object) -> str:
    return str(value or "").strip()


def _resolve_duration_seconds(duration_value: object) -> int:
    normalized = _normalize_string(duration_value).lower()
    return DURATION_MAP.get(normalized, DEFAULT_DURATION)


def _write_timeline_plan(timeline_plan: dict) -> None:
    TIMELINE_PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    with TIMELINE_PLAN_PATH.open("w", encoding="utf-8") as file:
        json.dump(timeline_plan, file, ensure_ascii=False, indent=2)


def build_timeline_plan(scheduler_output: dict) -> dict:
    print("[M4-TIMELINE] start")

    source_scenes = _normalize_scenes((scheduler_output or {}).get("scenes"))
    print(f"[M4-TIMELINE] scene_count={len(source_scenes)}")

    timeline_clips = []
    current_time = 0

    for scene in source_scenes:
        scene_id = _normalize_string(scene.get("scene_id"))
        for clip in _normalize_clips(scene.get("clips")):
            asset = _normalize_asset(clip.get("asset"))
            if not asset:
                continue

            duration_seconds = _resolve_duration_seconds(clip.get("duration"))
            start_time = current_time
            end_time = current_time + duration_seconds

            if start_time < 0 or end_time <= start_time:
                continue

            timeline_clips.append(
                {
                    "clip_id": _normalize_string(clip.get("clip_id")),
                    "scene_id": scene_id,
                    "asset": asset,
                    "start_time": start_time,
                    "end_time": end_time,
                    "duration": duration_seconds,
                    "text": _normalize_string(clip.get("text")),
                    "timeline_hints": {
                        "ready_for_render": False,
                    },
                }
            )
            current_time = end_time

    timeline_plan = {
        "timeline_mode": "timeline_v2",
        "timeline_duration": current_time,
        "timeline_tracks": [
            {
                "track_id": "track_001",
                "type": "video",
                "clips": timeline_clips,
            }
        ],
    }

    _write_timeline_plan(timeline_plan)

    print(f"[M4-TIMELINE] clip_count={len(timeline_clips)}")
    print(f"[M4-TIMELINE] timeline_duration={current_time}")
    print("[M4-TIMELINE] done")
    return timeline_plan