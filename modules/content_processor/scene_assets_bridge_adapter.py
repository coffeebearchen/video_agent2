# -*- coding: utf-8 -*-
"""
正式 Scene Assets Bridge V1 adapter。

职责：
1. 将 formal scene_bridge_plan 整理为 scene_assets 层可消费的素材请求结构
2. 只做 bridge -> asset request plan 的映射与落盘
3. 不做 candidate asset 真检索
4. 不做 asset selection execution
5. 不做 scene_clip_scheduler 调用
6. 不做 timeline / render / video assembly
7. 不替换旧视频主链，只为后续 scene_assets -> scheduler 接入做准备
"""

from __future__ import annotations

import json
from pathlib import Path


DEFAULT_BRIDGE_MODE = "scene_assets_bridge_v1"
DEFAULT_SOURCE_PRIORITY = ["immediate", "private", "public", "text"]
DEFAULT_NEXT_EXPECTED_STAGE = "candidate_asset_collection"
DEFAULT_ASSET_REQUEST_HINTS = {
    "needs_candidate_assets": True,
    "asset_selection_executed": False,
    "ready_for_scheduler": False,
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SCENE_ASSETS_BRIDGE_PLAN_PATH = PROJECT_ROOT / "data" / "current" / "scene_assets_bridge_plan.json"


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


def _normalize_bridge_scenes(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []

    results: list[dict] = []
    for item in value:
        if isinstance(item, dict):
            results.append(item)
    return results


def _write_scene_assets_bridge_plan(scene_assets_bridge_plan: dict) -> None:
    SCENE_ASSETS_BRIDGE_PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SCENE_ASSETS_BRIDGE_PLAN_PATH.open("w", encoding="utf-8") as file:
        json.dump(scene_assets_bridge_plan, file, ensure_ascii=False, indent=2)


def _build_asset_request_scene(bridge_scene: dict, request_index: int) -> dict:
    source_priority = _normalize_string_list(bridge_scene.get("source_priority")) or list(DEFAULT_SOURCE_PRIORITY)
    return {
        "asset_request_id": f"asset_req_{request_index + 1:03d}",
        "bridge_scene_id": _normalize_string(bridge_scene.get("bridge_scene_id")) or f"bridge_scene_{request_index + 1:03d}",
        "scene_id": _normalize_string(bridge_scene.get("scene_id")) or f"scene_{request_index + 1:03d}",
        "segment_id": _normalize_string(bridge_scene.get("segment_id")) or f"seg_{request_index + 1:03d}",
        "text": _normalize_string(bridge_scene.get("text")),
        "role": _normalize_string(bridge_scene.get("role")),
        "emphasis": _normalize_string(bridge_scene.get("emphasis")),
        "visual_preference": _normalize_string(bridge_scene.get("visual_preference")),
        "asset_hint_ids": _normalize_string_list(bridge_scene.get("asset_hint_ids")),
        "source_priority": source_priority,
        "fallback_mode": _normalize_string(bridge_scene.get("fallback_mode")) or "text_card",
        "duration_hint": _normalize_string(bridge_scene.get("duration_hint")) or "medium",
        "asset_request_hints": dict(DEFAULT_ASSET_REQUEST_HINTS),
    }


def build_scene_assets_bridge_plan(content_package: dict, scene_bridge_plan: dict) -> dict:
    source_content_package = content_package if isinstance(content_package, dict) else {}
    source_scene_bridge_plan = scene_bridge_plan if isinstance(scene_bridge_plan, dict) else {}
    bridge_scenes = _normalize_bridge_scenes(source_scene_bridge_plan.get("scenes"))

    asset_request_scenes = [
        _build_asset_request_scene(bridge_scene, request_index)
        for request_index, bridge_scene in enumerate(bridge_scenes)
    ]
    scene_assets_bridge_plan = {
        "bridge_mode": DEFAULT_BRIDGE_MODE,
        "source_bridge_mode": _normalize_string(source_scene_bridge_plan.get("bridge_mode")),
        "content_mode": _normalize_string(source_content_package.get("content_mode")),
        "style_mode": _normalize_string(source_content_package.get("style_mode")),
        "asset_request_scenes": asset_request_scenes,
        "asset_request_global_hints": {
            "bridge_target": "scene_assets",
            "next_expected_stage": DEFAULT_NEXT_EXPECTED_STAGE,
            "scheduler_attached": False,
            "render_attached": False,
        },
    }

    _write_scene_assets_bridge_plan(scene_assets_bridge_plan)

    print(f"[SCENE_ASSETS_BRIDGE] bridge_mode={scene_assets_bridge_plan['bridge_mode']}")
    print(f"[SCENE_ASSETS_BRIDGE] source_bridge_mode={scene_assets_bridge_plan['source_bridge_mode']}")
    print(f"[SCENE_ASSETS_BRIDGE] asset_request_scene_count={len(asset_request_scenes)}")
    print(f"[SCENE_ASSETS_BRIDGE] next_expected_stage={DEFAULT_NEXT_EXPECTED_STAGE}")

    return scene_assets_bridge_plan