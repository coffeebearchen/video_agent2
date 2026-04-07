# -*- coding: utf-8 -*-
"""
正式 Candidate Assets V1 collector。

职责：
1. 将 formal scene_assets_bridge_plan 整理为候选素材池
2. 只做 asset request -> candidate assets 的占位映射与落盘
3. 不做真实素材检索
4. 不做 selection
5. 不做 scene_clip_scheduler 调用
6. 不做 timeline / render / video assembly
7. 不替换旧视频主链，只为后续 scene_clip_scheduler 接入做准备
"""

from __future__ import annotations

import json
from pathlib import Path


DEFAULT_COLLECTOR_MODE = "candidate_assets_v1"
DEFAULT_NEXT_EXPECTED_STAGE = "scene_clip_scheduler"
DEFAULT_CANDIDATE_SCHEMAS = [
    {"type": "generated_stub", "source": "immediate", "description": "auto placeholder visual"},
    {"type": "stock_stub", "source": "public", "description": "generic stock placeholder"},
]
DEFAULT_DURATION_ESTIMATE = "short"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CANDIDATE_ASSETS_PLAN_PATH = PROJECT_ROOT / "data" / "current" / "candidate_assets_plan.json"


def _normalize_string(value: object) -> str:
    return str(value or "").strip()


def _normalize_asset_request_scenes(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []

    results: list[dict] = []
    for item in value:
        if isinstance(item, dict):
            results.append(item)
    return results


def _write_candidate_assets_plan(candidate_assets_plan: dict) -> None:
    CANDIDATE_ASSETS_PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    with CANDIDATE_ASSETS_PLAN_PATH.open("w", encoding="utf-8") as file:
        json.dump(candidate_assets_plan, file, ensure_ascii=False, indent=2)


def _build_candidates(scene_index: int) -> list[dict]:
    candidates = []
    for candidate_index, schema in enumerate(DEFAULT_CANDIDATE_SCHEMAS, start=1):
        candidates.append(
            {
                "candidate_id": f"cand_{scene_index + 1:03d}_{candidate_index:02d}",
                "type": schema["type"],
                "source": schema["source"],
                "description": schema["description"],
                "duration_estimate": DEFAULT_DURATION_ESTIMATE,
            }
        )
    return candidates


def _build_candidate_scene(asset_request_scene: dict, scene_index: int) -> dict:
    candidates = _build_candidates(scene_index)
    return {
        "candidate_scene_id": f"cand_scene_{scene_index + 1:03d}",
        "asset_request_id": _normalize_string(asset_request_scene.get("asset_request_id")) or f"asset_req_{scene_index + 1:03d}",
        "bridge_scene_id": _normalize_string(asset_request_scene.get("bridge_scene_id")) or f"bridge_scene_{scene_index + 1:03d}",
        "scene_id": _normalize_string(asset_request_scene.get("scene_id")) or f"scene_{scene_index + 1:03d}",
        "text": _normalize_string(asset_request_scene.get("text")),
        "visual_preference": _normalize_string(asset_request_scene.get("visual_preference")),
        "candidates": candidates,
        "candidate_hints": {
            "candidate_count": len(candidates),
            "ready_for_scheduler": False,
            "selection_done": False,
        },
    }


def build_candidate_assets_plan(content_package: dict, scene_assets_bridge_plan: dict) -> dict:
    source_scene_assets_bridge_plan = scene_assets_bridge_plan if isinstance(scene_assets_bridge_plan, dict) else {}
    asset_request_scenes = _normalize_asset_request_scenes(source_scene_assets_bridge_plan.get("asset_request_scenes"))

    candidate_scenes = [
        _build_candidate_scene(asset_request_scene, scene_index)
        for scene_index, asset_request_scene in enumerate(asset_request_scenes)
    ]
    total_candidates = sum(len(scene.get("candidates", [])) for scene in candidate_scenes)
    candidate_assets_plan = {
        "collector_mode": DEFAULT_COLLECTOR_MODE,
        "source_bridge_mode": _normalize_string(source_scene_assets_bridge_plan.get("bridge_mode")),
        "candidate_scenes": candidate_scenes,
        "collector_global_hints": {
            "next_expected_stage": DEFAULT_NEXT_EXPECTED_STAGE,
            "scheduler_attached": False,
            "render_attached": False,
        },
    }

    _write_candidate_assets_plan(candidate_assets_plan)

    print(f"[CANDIDATE_ASSETS] collector_mode={candidate_assets_plan['collector_mode']}")
    print(f"[CANDIDATE_ASSETS] candidate_scene_count={len(candidate_scenes)}")
    print(f"[CANDIDATE_ASSETS] total_candidates={total_candidates}")
    print(f"[CANDIDATE_ASSETS] next_expected_stage={DEFAULT_NEXT_EXPECTED_STAGE}")

    return candidate_assets_plan