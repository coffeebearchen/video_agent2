from __future__ import annotations

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
        "fade_enabled": True,
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
            "font_size": 62,
            "max_width": 940,
            "position_y": 92,
            "text_color": (255, 246, 235, 255),
            "bg_color": (54, 30, 18, 165),
            "padding_x": 34,
            "padding_y": 22,
            "radius": 28,
        },
        highlight_overrides={
            "font_size": 64,
            "max_width": 780,
            "position_ratio_y": 0.43,
            "text_color": (255, 196, 115, 255),
            "bg_color": (48, 28, 18, 205),
            "padding_x": 34,
            "padding_y": 24,
            "radius": 30,
            "min_start": 0.9,
            "start_ratio": 0.34,
        },
    ),
    "creator_clean": _build_style_preset(
        "creator_clean",
        title_overrides={
            "font_size": 58,
            "max_width": 920,
            "position_y": 96,
            "text_color": (248, 249, 250, 255),
            "bg_color": (10, 10, 10, 145),
            "padding_x": 28,
            "padding_y": 20,
            "radius": 24,
        },
        highlight_overrides={
            "font_size": 60,
            "max_width": 760,
            "position_ratio_y": 0.42,
            "text_color": (255, 179, 71, 255),
            "bg_color": (25, 25, 25, 190),
            "padding_x": 28,
            "padding_y": 20,
            "radius": 24,
            "min_start": 0.8,
            "start_ratio": 0.35,
        },
    ),
    "product_focus": _build_style_preset(
        "product_focus",
        title_overrides={
            "font_size": 60,
            "max_width": 940,
            "position_y": 90,
            "text_color": (255, 250, 243, 255),
            "bg_color": (18, 18, 18, 178),
            "padding_x": 30,
            "padding_y": 20,
            "radius": 20,
        },
        highlight_overrides={
            "font_size": 66,
            "max_width": 800,
            "position_ratio_y": 0.41,
            "text_color": (255, 144, 36, 255),
            "bg_color": (18, 18, 18, 220),
            "padding_x": 34,
            "padding_y": 24,
            "radius": 20,
            "min_start": 0.75,
            "start_ratio": 0.33,
        },
    ),
    "life_story": _build_style_preset(
        "life_story",
        title_overrides={
            "font_size": 54,
            "max_width": 900,
            "position_y": 108,
            "text_color": (250, 247, 244, 255),
            "bg_color": (80, 68, 60, 118),
            "padding_x": 26,
            "padding_y": 18,
            "radius": 30,
        },
        highlight_overrides={
            "font_size": 56,
            "max_width": 740,
            "position_ratio_y": 0.47,
            "text_color": (255, 205, 144, 255),
            "bg_color": (92, 82, 74, 150),
            "padding_x": 30,
            "padding_y": 22,
            "radius": 34,
            "min_start": 1.0,
            "start_ratio": 0.38,
        },
    ),
    "ai_control_lab": _build_style_preset(
        "ai_control_lab",
        title_overrides={
            "font_size": 56,
            "max_width": 930,
            "position_y": 92,
            "text_color": (232, 247, 250, 255),
            "bg_color": (8, 28, 36, 172),
            "padding_x": 28,
            "padding_y": 18,
            "radius": 16,
        },
        highlight_overrides={
            "font_size": 58,
            "max_width": 770,
            "position_ratio_y": 0.40,
            "text_color": (105, 225, 235, 255),
            "bg_color": (6, 32, 40, 212),
            "padding_x": 28,
            "padding_y": 20,
            "radius": 16,
            "min_start": 0.7,
            "start_ratio": 0.32,
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