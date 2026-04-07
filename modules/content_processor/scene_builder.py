# -*- coding: utf-8 -*-
"""
正式 Scene Layer V1 builder。

职责：
1. 将 formal expression package 转换为第一版 scene package
2. 只做 expression -> scene structure 的稳定映射
3. 不进入 asset matching / timeline / render / video assembly
"""

from __future__ import annotations


DEFAULT_SCENE_MODE = "scene_v1_linear"
DEFAULT_SOURCE_PRIORITY = ["immediate", "private", "public", "text"]
DEFAULT_FALLBACK_MODE = "text_card"
DEFAULT_SOURCE_PRIORITY_POLICY = "immediate_first"
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


def _normalize_segments(value: object) -> list[dict]:
    if not isinstance(value, list):
        return []

    results: list[dict] = []
    for item in value:
        if isinstance(item, dict):
            results.append(item)
    return results


def _normalize_global_visual_hints(value: object) -> dict:
    return value if isinstance(value, dict) else {}


def _resolve_fallback_mode(visual_preference: str) -> str:
    if visual_preference == "video_preferred":
        return "video_or_text"
    return DEFAULT_FALLBACK_MODE


def _resolve_duration_hint(role: str) -> str:
    if role == "body":
        return "medium"
    return "short"


def build_scene_package(content_package: dict, expression_package: dict) -> dict:
    source_content_package = content_package if isinstance(content_package, dict) else {}
    source_expression_package = expression_package if isinstance(expression_package, dict) else {}
    segments = _normalize_segments(source_expression_package.get("segments"))
    global_visual_hints = _normalize_global_visual_hints(source_expression_package.get("global_visual_hints"))

    scenes = []
    for scene_index, segment in enumerate(segments):
        role = _normalize_string(segment.get("role"))
        visual_preference = _normalize_string(segment.get("visual_preference"))
        scenes.append(
            {
                "scene_id": f"scene_{scene_index + 1:03d}",
                "segment_id": _normalize_string(segment.get("segment_id")) or f"seg_{scene_index + 1:03d}",
                "line_index": int(segment.get("line_index", scene_index) or 0),
                "role": role,
                "text": _normalize_string(segment.get("text")),
                "emphasis": _normalize_string(segment.get("emphasis")),
                "visual_preference": visual_preference,
                "asset_hint_ids": _normalize_string_list(segment.get("asset_hint_ids")),
                "source_priority": list(DEFAULT_SOURCE_PRIORITY),
                "fallback_mode": _resolve_fallback_mode(visual_preference),
                "duration_hint": _resolve_duration_hint(role),
            }
        )

    return {
        "scene_mode": DEFAULT_SCENE_MODE,
        "source_expression_mode": _normalize_string(source_expression_package.get("expression_mode")),
        "content_mode": _normalize_string(source_content_package.get("content_mode")),
        "style_mode": _normalize_string(source_content_package.get("style_mode")),
        "scenes": scenes,
        "scene_global_hints": {
            "preferred_pacing": _normalize_string(global_visual_hints.get("preferred_pacing")) or DEFAULT_PREFERRED_PACING,
            "highlight_keywords": _normalize_string_list(global_visual_hints.get("highlight_keywords")),
            "source_priority_policy": DEFAULT_SOURCE_PRIORITY_POLICY,
        },
    }