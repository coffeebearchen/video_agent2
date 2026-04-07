from __future__ import annotations

# Style system freeze:
# 1. STYLE_PRESETS is the single source of truth for overlay style parameters.
#    Visual style fields must not be duplicated in runners, renderers, or other modules.
# 2. Static style debugging should default to runner/frame_preview_runner.py.
#    Video preview remains for final acceptance, not first-pass style iteration.
# 3. Treat style in two layers:
#    - skeleton: title/highlight relationship, layout center of gravity, rhythm tendency, expression temperament
#    - skin: font, size, color, radius, padding, opacity, shadow strength
#    Skin can change frequently; skeleton should move carefully.

import os
from copy import deepcopy
from typing import Dict, List, Tuple

from modules.text_spec import build_default_text_spec


DEFAULT_STYLE_NAME = "creator_clean"
STYLE_NAME_ENV_KEY = "OVERLAY_STYLE_NAME"


# 统一管理 overlay 的表达规格。
# 本模块只负责规格与规则，不负责视频渲染与素材调度。
def _build_style_preset(
    style_name: str,
    title_overrides: Dict,
    highlight_overrides: Dict,
    behavior_overrides: Dict | None = None,
) -> dict:
    text_spec = build_default_text_spec(style_name)
    title_spec = {
        "enabled": True,
        "mode": str(text_spec.get("title", {}).get("mode", "persistent") or "persistent"),
        "font_size": 58,
        "max_width": 920,
        "position_mode": "top-center",
        "position_y": 96,
        "text_color": (248, 249, 250, 255),
        "bg_color": (10, 10, 10, 145),
        "padding_x": 28,
        "padding_y": 20,
        "radius": 24,
        "max_chars": 20,
    }
    title_spec.update(title_overrides or {})

    highlight_spec = {
        "enabled": True,
        "max_count": 1,
        "display_mode": str(text_spec.get("highlight", {}).get("mode", "single_card") or "single_card"),
        "bilingual_mode": str(text_spec.get("highlight", {}).get("layout", "zh_en_stacked") or "zh_en_stacked"),
        "font_size": 60,
        "max_width": 760,
        "position_mode": "center",
        "position_ratio_y": 0.42,
        "text_color": (255, 179, 71, 255),
        "bg_color": (25, 25, 25, 190),
        "padding_x": 28,
        "padding_y": 20,
        "radius": 24,
        "duration_mode": "fixed_3s",
        "fixed_duration": float(text_spec.get("highlight", {}).get("duration", 3.0) or 3.0),
        "min_start": 0.8,
        "start_ratio": 0.35,
        "semantic_min_ratio": 0.45,
        "semantic_max_ratio": 0.60,
        "fade_enabled": True,
        # Bilingual rendering parameters (V1: zh/en split control)
        # Fallback enabled: if missing or error, auto-revert to single-text mode
        "zh_text_color": None,  # If None, uses text_color, else overrides for Chinese only
        "en_text_color": None,  # If None, uses text_color, else overrides for English only
        "zh_font_size": None,   # If None, uses font_size, else overrides for Chinese only
        "en_font_size": None,   # If None, uses font_size, else overrides for English only
        "zh_en_gap": 10,        # Gap between zh and en in stacked/inline mode (pixels)
        "bilingual_render_enabled": True,  # Master switch: if False, use old single-text logic
    }
    highlight_spec.update(highlight_overrides or {})

    behavior_spec = {
        "conclusion_enabled": False,
        "allow_multiple_highlights": False,
        "allow_style_override": True,
    }
    behavior_spec.update(behavior_overrides or {})

    return {
        "style_name": style_name,
        "text_spec": text_spec,
        "title": title_spec,
        "highlight": highlight_spec,
        "behavior": behavior_spec,
    }


STYLE_PRESETS = {
    "personal_ip": _build_style_preset(
        "personal_ip",
        title_overrides={
            "font_size": 86,
            "max_width": 1020,
            "position_mode": "statement-zone",
            "position_y": 176,
            "text_color": (255, 255, 255, 255),
            "bg_color": (8, 8, 8, 244),
            "padding_x": 52,
            "padding_y": 30,
            "radius": 6,
            "max_chars": 24,
        },
        highlight_overrides={
            "font_size": 104,
            "max_width": 1040,
            "position_mode": "impact-offset",
            "position_ratio_y": 0.34,
            "text_color": (12, 12, 12, 255),
            "bg_color": (255, 214, 10, 248),
            "padding_x": 54,
            "padding_y": 34,
            "radius": 4,
            "min_start": 0.18,
            "start_ratio": 0.12,
            "semantic_min_ratio": 0.18,
            "semantic_max_ratio": 0.34,
            "fade_enabled": False,
            "zh_text_color": (12, 12, 12, 255),
            "en_text_color": (12, 12, 12, 255),
            "zh_font_size": 104,
            "en_font_size": 76,
            "zh_en_gap": 20,
            "bilingual_render_enabled": True,
        },
    ),
    "creator_clean": _build_style_preset(
        "creator_clean",
        title_overrides={
            "font_size": 42,
            "max_width": 760,
            "position_mode": "balanced-top-center",
            "position_y": 96,
            "text_color": (246, 247, 248, 255),
            "bg_color": (88, 94, 102, 138),
            "padding_x": 18,
            "padding_y": 12,
            "radius": 12,
            "max_chars": 12,
        },
        highlight_overrides={
            "font_size": 46,
            "max_width": 420,
            "position_mode": "center-lower",
            "position_ratio_y": 0.60,
            "text_color": (252, 252, 252, 255),
            "bg_color": (108, 114, 122, 198),
            "padding_x": 16,
            "padding_y": 12,
            "radius": 10,
            "min_start": 1.20,
            "start_ratio": 0.40,
            "semantic_min_ratio": 0.48,
            "semantic_max_ratio": 0.62,
            "fade_enabled": True,
            "zh_text_color": (252, 252, 252, 255),
            "en_text_color": (180, 184, 190, 220),
            "zh_font_size": 46,
            "en_font_size": 32,
            "zh_en_gap": 8,
            "bilingual_render_enabled": True,
        },
    ),
    "product_focus": _build_style_preset(
        "product_focus",
        title_overrides={
            "font_size": 82,
            "max_width": 1040,
            "position_mode": "poster-header",
            "position_y": 56,
            "text_color": (232, 244, 255, 255),
            "bg_color": (10, 58, 132, 244),
            "padding_x": 44,
            "padding_y": 24,
            "radius": 4,
            "max_chars": 20,
        },
        highlight_overrides={
            "font_size": 100,
            "max_width": 1000,
            "position_mode": "bottom-poster",
            "position_ratio_y": 0.82,
            "text_color": (255, 149, 0, 255),
            "bg_color": (0, 36, 92, 248),
            "padding_x": 52,
            "padding_y": 30,
            "radius": 2,
            "min_start": 0.24,
            "start_ratio": 0.16,
            "semantic_min_ratio": 0.20,
            "semantic_max_ratio": 0.36,
            "fade_enabled": False,
            "zh_text_color": (255, 149, 0, 255),
            "en_text_color": (232, 244, 255, 200),
            "zh_font_size": 100,
            "en_font_size": 72,
            "zh_en_gap": 16,
            "bilingual_render_enabled": True,
        },
    ),
    "life_story": _build_style_preset(
        "life_story",
        title_overrides={
            "font_size": 58,
            "max_width": 840,
            "position_mode": "lower-narrative",
            "position_y": 820,
            "text_color": (255, 243, 226, 255),
            "bg_color": (180, 114, 72, 214),
            "padding_x": 42,
            "padding_y": 28,
            "radius": 54,
            "max_chars": 22,
        },
        highlight_overrides={
            "font_size": 72,
            "max_width": 820,
            "position_mode": "deep-lower-third",
            "position_ratio_y": 0.76,
            "text_color": (255, 234, 205, 255),
            "bg_color": (228, 146, 92, 216),
            "padding_x": 46,
            "padding_y": 34,
            "radius": 60,
            "min_start": 2.20,
            "start_ratio": 0.62,
            "semantic_min_ratio": 0.70,
            "semantic_max_ratio": 0.88,
            "fade_enabled": True,
            "zh_text_color": (255, 234, 205, 255),
            "en_text_color": (255, 243, 226, 200),
            "zh_font_size": 72,
            "en_font_size": 56,
            "zh_en_gap": 14,
            "bilingual_render_enabled": True,
        },
    ),
    "ai_control_lab": _build_style_preset(
        "ai_control_lab",
        title_overrides={
            "font_size": 44,
            "max_width": 560,
            "position_mode": "hud-top-left",
            "position_y": 34,
            "text_color": (120, 247, 255, 255),
            "bg_color": (0, 20, 56, 246),
            "padding_x": 16,
            "padding_y": 10,
            "radius": 2,
            "max_chars": 10,
        },
        highlight_overrides={
            "font_size": 62,
            "max_width": 620,
            "position_mode": "hud-upper-band",
            "position_ratio_y": 0.18,
            "text_color": (86, 255, 240, 255),
            "bg_color": (0, 44, 110, 248),
            "padding_x": 20,
            "padding_y": 14,
            "radius": 2,
            "min_start": 3.20,
            "start_ratio": 0.74,
            "semantic_min_ratio": 0.82,
            "semantic_max_ratio": 0.94,
            "fade_enabled": False,
            "zh_text_color": (86, 255, 240, 255),
            "en_text_color": (120, 200, 220, 200),
            "zh_font_size": 62,
            "en_font_size": 46,
            "zh_en_gap": 12,
            "bilingual_render_enabled": True,
        },
    ),
}


def get_runtime_style_name(style_name: str | None = None) -> str:
    requested_style = str(style_name or "").strip()
    if requested_style:
        return requested_style if requested_style in STYLE_PRESETS else DEFAULT_STYLE_NAME

    env_style = str(os.environ.get(STYLE_NAME_ENV_KEY, "") or "").strip()
    if env_style in STYLE_PRESETS:
        return env_style

    return DEFAULT_STYLE_NAME


def get_overlay_style(style_name: str = DEFAULT_STYLE_NAME) -> dict:
    resolved_style_name = get_runtime_style_name(style_name)
    preset = STYLE_PRESETS.get(resolved_style_name) or STYLE_PRESETS[DEFAULT_STYLE_NAME]
    return deepcopy(preset)


def get_text_spec(style_name: str = DEFAULT_STYLE_NAME) -> dict:
    resolved_style_name = get_runtime_style_name(style_name)
    return deepcopy(build_default_text_spec(resolved_style_name))


def get_title_spec(style_name: str = DEFAULT_STYLE_NAME) -> dict:
    return get_overlay_style(style_name).get("title", {})


def get_highlight_spec(style_name: str = DEFAULT_STYLE_NAME) -> dict:
    return get_overlay_style(style_name).get("highlight", {})


def get_behavior_spec(style_name: str = DEFAULT_STYLE_NAME) -> dict:
    return get_overlay_style(style_name).get("behavior", {})


def emit_text_spec_debug(style_name: str = DEFAULT_STYLE_NAME) -> None:
    text_spec = get_text_spec(style_name)
    highlight_spec = text_spec.get("highlight", {})
    print(f"[TEXT_SPEC] highlight_duration={highlight_spec.get('duration', 3.0)}")
    print(f"[TEXT_SPEC] layout={highlight_spec.get('layout', 'zh_en_stacked')}")


def normalize_highlight_count(items: List[str], style_name: str = DEFAULT_STYLE_NAME) -> List[str]:
    highlight_spec = get_highlight_spec(style_name)
    behavior_spec = get_behavior_spec(style_name)
    max_count = int(highlight_spec.get("max_count", 1) or 1)

    if behavior_spec.get("allow_multiple_highlights"):
        limit = max(1, max_count)
    else:
        limit = 1

    results: List[str] = []
    for item in items or []:
        word = str(item or "").strip()
        if not word or word in results:
            continue
        results.append(word)
        if len(results) >= limit:
            break
    return results


def _clamp_window(start: float, desired_duration: float, total_duration: float) -> Tuple[float, float]:
    safe_total = max(0.1, float(total_duration or 0.0))
    safe_start = max(0.0, min(float(start or 0.0), max(0.0, safe_total - 0.1)))
    safe_duration = max(0.1, min(float(desired_duration or 0.0), max(0.1, safe_total - safe_start)))
    return safe_start, safe_duration


def resolve_title_timing(scene_duration: float, style_name: str = DEFAULT_STYLE_NAME) -> Tuple[float, float]:
    text_spec = get_text_spec(style_name)
    mode = str(text_spec.get("title", {}).get("mode", "persistent") or "persistent")
    safe_scene_duration = max(0.1, float(scene_duration or 0.0))

    if mode == "persistent":
        return 0.0, safe_scene_duration

    return 0.0, safe_scene_duration


def resolve_highlight_timing(scene_duration: float, style_name: str = DEFAULT_STYLE_NAME) -> Tuple[float, float]:
    highlight_spec = get_highlight_spec(style_name)
    text_spec = get_text_spec(style_name)
    duration_mode = str(highlight_spec.get("duration_mode", "fixed_3s") or "fixed_3s")
    safe_scene_duration = max(0.1, float(scene_duration or 0.0))

    if duration_mode == "fixed_3s":
        start = max(
            float(highlight_spec.get("min_start", 0.8) or 0.8),
            safe_scene_duration * float(highlight_spec.get("start_ratio", 0.35) or 0.35),
        )
        duration = min(
            float(text_spec.get("highlight", {}).get("duration", 3.0) or 3.0),
            safe_scene_duration * 0.6,
        )
        return _clamp_window(start, duration, safe_scene_duration)

    return _clamp_window(0.0, min(3.0, safe_scene_duration), safe_scene_duration)


def build_highlight_display_text(chinese: str, english: str, style_name: str = DEFAULT_STYLE_NAME) -> str:
    text_spec = get_text_spec(style_name)
    bilingual_mode = str(text_spec.get("highlight", {}).get("layout", "zh_en_stacked") or "zh_en_stacked")
    zh_text = str(chinese or "").strip()
    en_text = str(english or "").strip()

    if bilingual_mode == "zh_only":
        return zh_text

    if bilingual_mode == "en_only":
        return en_text

    if bilingual_mode == "zh_en_inline":
        if zh_text and en_text:
            return f"{zh_text} / {en_text}"
        return zh_text or en_text

    if bilingual_mode == "zh_en_stacked":
        if zh_text and en_text:
            return f"{zh_text}\n{en_text}"
        return zh_text or en_text

    return zh_text or en_text