# -*- coding: utf-8 -*-
"""
正式 Selected Assets V1 selector stub。

职责：
1. 将 formal candidate_assets_plan 整理为当前选定素材结果
2. 只做 candidate -> selected 的稳定映射与落盘
3. 不做真实素材检索
4. 不做 selection ranking 扩展
5. 不做 scene_clip_scheduler 调用
6. 不做 timeline / render / video assembly
7. 不替换旧视频主链，只为后续 scene_clip_scheduler 接入做准备
"""

from __future__ import annotations

import json
from pathlib import Path


DEFAULT_SELECTOR_MODE = "selected_assets_v1"
DEFAULT_SELECTION_STRATEGY = "first_candidate_safe_pick"
DEFAULT_NEXT_EXPECTED_STAGE = "scene_clip_scheduler"

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SELECTED_ASSETS_PLAN_PATH = PROJECT_ROOT / "data" / "current" / "selected_assets_plan.json"


def _normalize_string(value: object) -> str:
    return str(value or "").strip()


def _normalize_candidate_scenes(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []

    results: list[dict] = []
    for item in value:
        if isinstance(item, dict):
            results.append(item)
    return results


def _normalize_candidates(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []

    results: list[dict] = []
    for item in value:
        if isinstance(item, dict):
            results.append(item)
    return results


def _write_selected_assets_plan(selected_assets_plan: dict) -> None:
    SELECTED_ASSETS_PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    with SELECTED_ASSETS_PLAN_PATH.open("w", encoding="utf-8") as file:
        json.dump(selected_assets_plan, file, ensure_ascii=False, indent=2)


def _select_first_candidate(candidate_scene: dict) -> dict:
    candidates = _normalize_candidates(candidate_scene.get("candidates"))
    if candidates:
        return dict(candidates[0])

    return {
        "candidate_id": "",
        "type": "missing_stub",
        "source": "none",
        "description": "no candidate available",
        "duration_estimate": "short",
    }


def _build_selected_scene(candidate_scene: dict, scene_index: int) -> dict:
    selected_asset = _select_first_candidate(candidate_scene)
    return {
        "selected_scene_id": f"sel_scene_{scene_index + 1:03d}",
        "candidate_scene_id": _normalize_string(candidate_scene.get("candidate_scene_id")) or f"cand_scene_{scene_index + 1:03d}",
        "scene_id": _normalize_string(candidate_scene.get("scene_id")) or f"scene_{scene_index + 1:03d}",
        "asset_request_id": _normalize_string(candidate_scene.get("asset_request_id")) or f"asset_req_{scene_index + 1:03d}",
        "text": _normalize_string(candidate_scene.get("text")),
        "visual_preference": _normalize_string(candidate_scene.get("visual_preference")),
        "selected_asset": selected_asset,
        "selection_hints": {
            "selection_done": True,
            "ready_for_scheduler": True,
            "selection_strategy": DEFAULT_SELECTION_STRATEGY,
        },
    }


def build_selected_assets_plan(content_package: dict, candidate_assets_plan: dict) -> dict:
    source_candidate_assets_plan = candidate_assets_plan if isinstance(candidate_assets_plan, dict) else {}
    candidate_scenes = _normalize_candidate_scenes(source_candidate_assets_plan.get("candidate_scenes"))

    selected_scenes = [
        _build_selected_scene(candidate_scene, scene_index)
        for scene_index, candidate_scene in enumerate(candidate_scenes)
    ]
    selected_assets_plan = {
        "selector_mode": DEFAULT_SELECTOR_MODE,
        "source_collector_mode": _normalize_string(source_candidate_assets_plan.get("collector_mode")),
        "selected_scenes": selected_scenes,
        "selector_global_hints": {
            "next_expected_stage": DEFAULT_NEXT_EXPECTED_STAGE,
            "scheduler_attached": False,
            "render_attached": False,
        },
    }

    _write_selected_assets_plan(selected_assets_plan)

    print(f"[SELECTED_ASSETS] selector_mode={selected_assets_plan['selector_mode']}")
    print(f"[SELECTED_ASSETS] selected_scene_count={len(selected_scenes)}")
    print(f"[SELECTED_ASSETS] selection_strategy={DEFAULT_SELECTION_STRATEGY}")
    print(f"[SELECTED_ASSETS] next_expected_stage={DEFAULT_NEXT_EXPECTED_STAGE}")

    return selected_assets_plan