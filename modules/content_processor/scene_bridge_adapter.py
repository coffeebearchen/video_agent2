# -*- coding: utf-8 -*-
"""
正式 Scene Bridge V1 adapter。

职责：
1. 将 formal scene_package 整理为稳定的 bridge 中间结构
2. 只做 scene -> bridge plan 的映射与落盘
3. 不做 asset matching
4. 不做 scene_assets 调用
5. 不做 scene_clip_scheduler 调用
6. 不做 timeline / render / video assembly
7. 不替换旧视频主链，只为后续桥接旧视频主链做准备
"""

from __future__ import annotations

import json
from pathlib import Path


DEFAULT_BRIDGE_MODE = "scene_bridge_v1"
DEFAULT_SOURCE_PRIORITY = ["immediate", "private", "public", "text"]
DEFAULT_NEXT_EXPECTED_STAGE = "scene_assets_or_scheduler"
DEFAULT_BRIDGE_HINTS = {
    "needs_asset_selection": True,
    "needs_timeline_resolution": True,
    "ready_for_render": False,
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCENE_BRIDGE_PLAN_PATH = PROJECT_ROOT / "data" / "current" / "scene_bridge_plan.json"


def _normalize_string(value: object) -> str:
    return str(value or "").strip()


def _normalize_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []

    results: list[str] = []
    for item in value:
        normalized = _normalize_string(item)
        if normalized:
            results.append(normalized)
    return results


def _normalize_scenes(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []

    results: list[dict] = []
    for item in value:
        if isinstance(item, dict):
            results.append(item)
    return results


def _write_scene_bridge_plan(scene_bridge_plan: dict) -> None:
    SCENE_BRIDGE_PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SCENE_BRIDGE_PLAN_PATH.open("w", encoding="utf-8") as file:
        json.dump(scene_bridge_plan, file, ensure_ascii=False, indent=2)


def _build_bridge_scene(scene: dict, bridge_index: int) -> dict:
    source_priority = _normalize_string_list(scene.get("source_priority")) or list(DEFAULT_SOURCE_PRIORITY)
    return {
        "bridge_scene_id": f"bridge_scene_{bridge_index + 1:03d}",
        "scene_id": _normalize_string(scene.get("scene_id")) or f"scene_{bridge_index + 1:03d}",
        "segment_id": _normalize_string(scene.get("segment_id")) or f"seg_{bridge_index + 1:03d}",
        "text": _normalize_string(scene.get("text")),
        "role": _normalize_string(scene.get("role")),
        "emphasis": _normalize_string(scene.get("emphasis")),
        "visual_preference": _normalize_string(scene.get("visual_preference")),
        "asset_hint_ids": _normalize_string_list(scene.get("asset_hint_ids")),
        "source_priority": source_priority,
        "fallback_mode": _normalize_string(scene.get("fallback_mode")) or "text_card",
        "duration_hint": _normalize_string(scene.get("duration_hint")) or "medium",
        "bridge_hints": dict(DEFAULT_BRIDGE_HINTS),
    }


def build_scene_bridge_plan(content_package: dict, scene_package: dict) -> dict:
    source_content_package = content_package if isinstance(content_package, dict) else {}
    source_scene_package = scene_package if isinstance(scene_package, dict) else {}
    source_scenes = _normalize_scenes(source_scene_package.get("scenes"))

    bridge_scenes = [_build_bridge_scene(scene, bridge_index) for bridge_index, scene in enumerate(source_scenes)]
    scene_bridge_plan = {
        "bridge_mode": DEFAULT_BRIDGE_MODE,
        "source_scene_mode": _normalize_string(source_scene_package.get("scene_mode")),
        "content_mode": _normalize_string(source_content_package.get("content_mode")),
        "style_mode": _normalize_string(source_content_package.get("style_mode")),
        "scenes": bridge_scenes,
        "bridge_global_hints": {
            "bridge_target": "legacy_video_pipeline",
            "next_expected_stage": DEFAULT_NEXT_EXPECTED_STAGE,
            "render_attached": False,
        },
    }

    _write_scene_bridge_plan(scene_bridge_plan)

    print(f"[SCENE_BRIDGE] bridge_mode={scene_bridge_plan['bridge_mode']}")
    print(f"[SCENE_BRIDGE] source_scene_mode={scene_bridge_plan['source_scene_mode']}")
    print(f"[SCENE_BRIDGE] bridge_scene_count={len(bridge_scenes)}")
    print(f"[SCENE_BRIDGE] next_expected_stage={DEFAULT_NEXT_EXPECTED_STAGE}")

    return scene_bridge_plan