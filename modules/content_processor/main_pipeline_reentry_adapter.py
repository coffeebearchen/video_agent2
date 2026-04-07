# -*- coding: utf-8 -*-
"""
新链 -> 旧主链回接 adapter。

职责：
1. 读取 timeline_plan 对应的数据结构
2. 转换为旧 video_engine 可接受的最小 scene_assets 输入结构
3. 落盘 main_pipeline_reentry_input.json 供隔离 runner 使用

边界：
1. 不改旧主链模块
2. 不做 render / overlay / scheduler 重写
3. 不重排时间，不做算法优化
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from modules import project_paths


PROJECT_ROOT = Path(project_paths.get_project_root())
DATA_CURRENT_DIR = Path(project_paths.get_data_current_dir())
MAIN_PIPELINE_REENTRY_INPUT_PATH = DATA_CURRENT_DIR / "main_pipeline_reentry_input.json"

IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".webm"}
DEFAULT_SECTION = "reentry"
DEFAULT_DURATION = 4.0


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    _ensure_parent(path)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def _to_float(value: Any, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    if number <= 0:
        return default
    return number


def _resolve_existing_local_path(candidate: Any) -> Optional[Path]:
    if not isinstance(candidate, str):
        return None

    raw_value = candidate.strip()
    if not raw_value:
        return None

    possible_path = Path(raw_value)
    if not possible_path.is_absolute():
        possible_path = PROJECT_ROOT / possible_path

    try:
        resolved = possible_path.resolve()
    except Exception:
        return None

    if resolved.exists() and resolved.is_file():
        return resolved
    return None


def _guess_legacy_asset_type(asset_type: Any, asset_path: Optional[Path]) -> str:
    if asset_path is not None:
        suffix = asset_path.suffix.lower()
        if suffix in IMAGE_SUFFIXES:
            return "image"
        if suffix in VIDEO_SUFFIXES:
            return "video"

    normalized = str(asset_type or "").strip().lower()
    if normalized in {"image", "video", "text_card"}:
        return normalized
    return "text_card"


def _pick_asset_path(asset: Dict[str, Any]) -> Optional[Path]:
    for key in ["file", "file_path", "asset_file", "url", "file_name"]:
        resolved = _resolve_existing_local_path(asset.get(key))
        if resolved is not None:
            return resolved
    return None


def _extract_video_track_clips(timeline_plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    tracks = timeline_plan.get("timeline_tracks", [])
    if not isinstance(tracks, list):
        return []

    for track in tracks:
        if not isinstance(track, dict):
            continue
        if str(track.get("type", "")).strip().lower() != "video":
            continue
        clips = track.get("clips", [])
        if isinstance(clips, list):
            return [clip for clip in clips if isinstance(clip, dict)]
    return []


def _build_scene_asset_record(clip: Dict[str, Any], index: int) -> Dict[str, Any]:
    asset = clip.get("asset", {})
    if not isinstance(asset, dict):
        asset = {}

    asset_path = _pick_asset_path(asset)
    legacy_type = _guess_legacy_asset_type(asset.get("asset_type") or asset.get("type"), asset_path)
    legacy_file = str(asset_path) if asset_path is not None else ""
    if not legacy_file:
        legacy_type = "text_card"

    duration = _to_float(
        clip.get("duration"),
        default=_to_float(
            _to_float(clip.get("end_time"), DEFAULT_DURATION) - _to_float(clip.get("start_time"), 0.0),
            DEFAULT_DURATION,
        ),
    )

    scene_text = str(clip.get("text", "") or "")
    clip_id = str(clip.get("clip_id", f"clip_{index + 1:03d}") or f"clip_{index + 1:03d}")
    scene_id = index
    asset_id = str(asset.get("asset_id") or clip_id)

    return {
        "type": legacy_type,
        "file": legacy_file,
        "scene_id": scene_id,
        "section": DEFAULT_SECTION,
        "asset_id": asset_id,
        "duration": duration,
        "asset_type": legacy_type,
        "asset_file": legacy_file,
        "text": scene_text,
        "highlights": [],
        "start": clip.get("start_time"),
        "source_scene_id": clip.get("scene_id"),
        "clip_id": clip_id,
        "timeline_start": clip.get("start_time"),
        "timeline_end": clip.get("end_time"),
        "timeline_duration": clip.get("duration"),
        "reentry_trace": {
            "input_source": "timeline_plan",
            "source_scene_id": clip.get("scene_id"),
            "clip_id": clip_id,
            "asset_source": asset.get("source"),
        },
    }


def build_main_pipeline_reentry_input(
    timeline_plan: Dict[str, Any],
    input_source: str = "timeline_plan",
) -> Dict[str, Any]:
    if not isinstance(timeline_plan, dict):
        raise ValueError("timeline_plan must be a JSON object")

    clips = _extract_video_track_clips(timeline_plan)
    if not clips:
        raise ValueError("timeline_plan does not contain any video clips")

    scene_assets = [_build_scene_asset_record(clip, index) for index, clip in enumerate(clips)]
    payload = {
        "stage": "main_pipeline_reentry",
        "adapter_mode": "main_pipeline_reentry_v1",
        "used_input_source": input_source,
        "target_old_entry": "modules.video_engine.main",
        "target_input_contract": "scene_assets.json",
        "scene_assets_count": len(scene_assets),
        "scene_assets": scene_assets,
    }
    _write_json(MAIN_PIPELINE_REENTRY_INPUT_PATH, payload)
    return payload