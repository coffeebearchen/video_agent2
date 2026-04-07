# -*- coding: utf-8 -*-
"""
Minimal runnable scene_clip_scheduler stub.

职责：
1. 接收 scheduler input plan
2. 输出最小 scheduler_output 结构
3. 仅用于 execution path 结构验证，不包含真实调度逻辑
"""

from __future__ import annotations


DEFAULT_DURATION = "short"


def _normalize_scenes(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []

    results: list[dict] = []
    for item in value:
        if isinstance(item, dict):
            results.append(item)
    return results


def _normalize_assets(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []

    results: list[dict] = []
    for item in value:
        if isinstance(item, dict):
            results.append(dict(item))
    return results


def _normalize_string(value: object) -> str:
    return str(value or "").strip()


def scene_clip_scheduler(input_plan: dict) -> dict:
    print("[SCHEDULER_STUB] start")

    if not isinstance(input_plan, dict):
        print("[SCHEDULER_STUB] scene_count=0")
        print("[SCHEDULER_STUB] clip_count=0")
        print("[SCHEDULER_STUB] done")
        return {"scenes": []}

    source_scenes = _normalize_scenes(input_plan.get("scenes"))
    print(f"[SCHEDULER_STUB] scene_count={len(source_scenes)}")

    output_scenes = []
    clip_counter = 0

    for scene in source_scenes:
        scene_id = _normalize_string(scene.get("scene_id"))
        text = _normalize_string(scene.get("text"))
        assets = _normalize_assets(scene.get("assets"))

        clips = []
        for asset in assets:
            clip_counter += 1
            clips.append(
                {
                    "clip_id": f"clip_{clip_counter:03d}",
                    "asset": asset,
                    "duration": _normalize_string(asset.get("duration_estimate")) or DEFAULT_DURATION,
                    "text": text,
                }
            )

        output_scenes.append(
            {
                "scene_id": scene_id,
                "clips": clips,
            }
        )

    print(f"[SCHEDULER_STUB] clip_count={clip_counter}")
    print("[SCHEDULER_STUB] done")
    return {"scenes": output_scenes}