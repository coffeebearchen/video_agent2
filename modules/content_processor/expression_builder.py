# -*- coding: utf-8 -*-
"""
正式 Expression Layer V1 builder。

职责：
1. 将 formal content package 转换为第一版 expression package
2. 只做 content -> expression structure 的稳定映射
3. 不进入 scene / timeline / asset matching / video assembly
"""

from __future__ import annotations


DEFAULT_EXPRESSION_MODE = "narrative_v1"
DEFAULT_SOURCE_PRIORITY = "user_uploaded_media_first"
DEFAULT_PREFERRED_PACING = "medium"


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


def _normalize_input_sources(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _get_asset_ids(group: object) -> list[str]:
    if not isinstance(group, dict):
        return []

    assets = group.get("assets")
    if not isinstance(assets, list):
        return []

    results: list[str] = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        asset_id = _normalize_string(asset.get("asset_id"))
        if asset_id:
            results.append(asset_id)
    return results


def _resolve_role(line_count: int, line_index: int) -> str:
    if line_count <= 1:
        return "hook"
    if line_count == 2:
        return "hook" if line_index == 0 else "close"
    if line_index == 0:
        return "hook"
    if line_index == line_count - 1:
        return "close"
    return "body"


def _resolve_emphasis(role: str) -> str:
    if role == "body":
        return "medium"
    return "high"


def _resolve_visual_preference(
    *,
    role: str,
    line_index: int,
    has_reference_images: bool,
    has_reference_videos: bool,
) -> str:
    if line_index == 0:
        return "image_or_text"
    if role == "close":
        return "text_only"
    if role == "body" and has_reference_videos:
        return "video_preferred"
    if role == "body" and has_reference_images:
        return "image_preferred"
    return "image_or_text"


def _resolve_asset_hint_ids(visual_preference: str, image_asset_ids: list[str], video_asset_ids: list[str]) -> list[str]:
    if visual_preference == "video_preferred":
        return video_asset_ids[:2]
    if visual_preference == "image_preferred":
        return image_asset_ids[:2]
    return []


def build_expression_package(content_package: dict) -> dict:
    source_package = content_package if isinstance(content_package, dict) else {}
    script_lines = _normalize_string_list(source_package.get("script"))
    highlights = _normalize_string_list(source_package.get("highlights"))
    input_sources = _normalize_input_sources(source_package.get("input_sources"))

    image_asset_ids = _get_asset_ids(input_sources.get("image_group"))
    video_asset_ids = _get_asset_ids(input_sources.get("video_group"))
    has_reference_images = bool(input_sources.get("has_reference_images")) or bool(image_asset_ids)
    has_reference_videos = bool(input_sources.get("has_reference_videos")) or bool(video_asset_ids)

    segments = []
    line_count = len(script_lines)
    for line_index, text in enumerate(script_lines):
        role = _resolve_role(line_count, line_index)
        visual_preference = _resolve_visual_preference(
            role=role,
            line_index=line_index,
            has_reference_images=has_reference_images,
            has_reference_videos=has_reference_videos,
        )
        segments.append(
            {
                "segment_id": f"seg_{line_index + 1:03d}",
                "line_index": line_index,
                "text": text,
                "role": role,
                "emphasis": _resolve_emphasis(role),
                "visual_preference": visual_preference,
                "asset_hint_ids": _resolve_asset_hint_ids(visual_preference, image_asset_ids, video_asset_ids),
            }
        )

    return {
        "expression_mode": DEFAULT_EXPRESSION_MODE,
        "title": _normalize_string(source_package.get("title")),
        "style_mode": _normalize_string(source_package.get("style_mode")),
        "content_mode": _normalize_string(source_package.get("content_mode")),
        "segments": segments,
        "global_visual_hints": {
            "preferred_pacing": DEFAULT_PREFERRED_PACING,
            "highlight_keywords": highlights,
            "source_priority": _normalize_string(input_sources.get("priority_policy")) or DEFAULT_SOURCE_PRIORITY,
        },
    }