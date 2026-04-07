# -*- coding: utf-8 -*-
"""
文件名：style_preview_service.py
作用说明：
1. 按多个 style_mode 批量生成 preview payload
2. 只负责串接 preview_payload_builder
3. 不负责展示格式、不负责底层模型逻辑
"""

from modules.preview_payload_builder import build_preview_payload


DEFAULT_STYLE_MODES = ["knowledge", "authority", "story"]


def _normalize_style_modes(style_modes: list[str] | None) -> list[str]:
    if not isinstance(style_modes, list) or not style_modes:
        return DEFAULT_STYLE_MODES[:]

    results: list[str] = []
    for style_mode in style_modes:
        normalized = str(style_mode or "").strip().lower()
        if not normalized or normalized in results:
            continue
        results.append(normalized)

    return results or DEFAULT_STYLE_MODES[:]


def build_style_previews(
    raw_text: str,
    content_mode: str,
    style_modes: list[str],
    user_intent: dict | None = None,
) -> list[dict]:
    """按给定风格列表批量生成 preview payload。"""
    preview_results: list[dict] = []

    for style_mode in _normalize_style_modes(style_modes):
        payload = build_preview_payload(
            raw_text=raw_text,
            content_mode=content_mode,
            style_mode=style_mode,
            user_intent=user_intent,
        )
        preview_results.append(
            {
                "style_mode": style_mode,
                "payload": payload,
            }
        )

    return preview_results