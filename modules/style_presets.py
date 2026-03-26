# -*- coding: utf-8 -*-
"""
文件名：style_presets.py
作用说明：
1. 定义可选风格预设名称
2. 定义各风格对默认配置的覆盖项
3. 定义各风格对表达模块的默认策略
4. 提供风格预设读取与 fallback 接口

本次改动点：
1. 为四种 style 正式绑定表达模块配置
2. 让 style 不只决定视觉，也决定表达策略
3. 保持现有 preset 结构不变，继续由 config.py 统一组装 runtime_config
"""

DEFAULT_STYLE_NAME = "serious"


STYLE_PRESETS = {
    "serious": {
        "expression_modules": {
            "segment_animation_enabled": False,
            "highlight_enabled": True,
            "highlight_emphasis_enabled": False,
            "default_segment_animation": "fade_in",
            "default_highlight_animation": "none",
            "highlight_emphasis_strength": 0.0,
        },
        "transition": {
            "default_fade_duration": 0.50,
            "soft_min_fade_duration": 0.30,
            "hard_min_fade_duration": 0.20,
            "base_fade_ratio": 0.16,
            "max_fade_ratio": 0.34,
        },
        "ui_card": {
            "card_fill": (10, 10, 14, 184),
            "card_border": (255, 255, 255, 40),
            "title_color": (198, 204, 214, 255),
            "text_font_size": 58,
            "label_font_size": 27,
        },
        "image_layout": {
            "dark_overlay_alpha": 52,
        },
        "motion": {
            "motion_canvas_scale": 1.18,
            "pan_travel_ratio": 0.62,
            "zoom_in_end_scale": 1.12,
            "zoom_out_start_scale": 1.12,
        },
    },
    "energetic": {
        "expression_modules": {
            "segment_animation_enabled": True,
            "highlight_enabled": True,
            "highlight_emphasis_enabled": True,
            "default_segment_animation": "slide_up",
            "default_highlight_animation": "pop",
            "highlight_emphasis_strength": 0.22,
        },
        "transition": {
            "default_fade_duration": 0.32,
            "soft_min_fade_duration": 0.22,
            "hard_min_fade_duration": 0.16,
            "base_fade_ratio": 0.11,
            "max_fade_ratio": 0.28,
        },
        "ui_card": {
            "card_fill": (14, 14, 18, 164),
            "card_border": (255, 255, 255, 54),
            "text_font_size": 62,
            "label_font_size": 26,
            "padding_x": 48,
            "padding_top": 30,
            "padding_bottom": 36,
        },
        "image_layout": {
            "dark_overlay_alpha": 34,
        },
        "motion": {
            "motion_canvas_scale": 1.28,
            "pan_travel_ratio": 0.84,
            "zoom_in_end_scale": 1.22,
            "zoom_out_start_scale": 1.22,
        },
    },
    "calm": {
        "expression_modules": {
            "segment_animation_enabled": True,
            "highlight_enabled": True,
            "highlight_emphasis_enabled": False,
            "default_segment_animation": "fade_in",
            "default_highlight_animation": "none",
            "highlight_emphasis_strength": 0.08,
        },
        "transition": {
            "default_fade_duration": 0.56,
            "soft_min_fade_duration": 0.34,
            "hard_min_fade_duration": 0.22,
            "base_fade_ratio": 0.18,
            "max_fade_ratio": 0.36,
        },
        "ui_card": {
            "card_fill": (10, 10, 14, 188),
            "title_color": (214, 218, 226, 255),
            "text_font_size": 58,
            "text_line_spacing": 20,
            "label_text_gap": 26,
        },
        "image_layout": {
            "dark_overlay_alpha": 58,
        },
        "motion": {
            "motion_canvas_scale": 1.16,
            "pan_travel_ratio": 0.50,
            "zoom_in_end_scale": 1.10,
            "zoom_out_start_scale": 1.10,
        },
    },
    "minimal": {
        "expression_modules": {
            "segment_animation_enabled": False,
            "highlight_enabled": False,
            "highlight_emphasis_enabled": False,
            "default_segment_animation": "fade_in",
            "default_highlight_animation": "none",
            "highlight_emphasis_strength": 0.0,
        },
        "transition": {
            "default_fade_duration": 0.38,
            "soft_min_fade_duration": 0.24,
            "hard_min_fade_duration": 0.16,
            "base_fade_ratio": 0.12,
            "max_fade_ratio": 0.30,
        },
        "ui_card": {
            "card_fill": (8, 8, 10, 146),
            "card_border": (255, 255, 255, 26),
            "card_radius": 24,
            "card_border_width": 1,
            "text_font_size": 56,
            "label_font_size": 24,
            "padding_x": 46,
            "padding_top": 28,
            "padding_bottom": 32,
            "label_text_gap": 20,
        },
        "image_layout": {
            "dark_overlay_alpha": 40,
        },
        "motion": {
            "motion_canvas_scale": 1.14,
            "pan_travel_ratio": 0.46,
            "zoom_in_end_scale": 1.08,
            "zoom_out_start_scale": 1.08,
        },
    },
}


def normalize_style_name(style_name):
    """标准化风格名称。"""
    if style_name is None:
        return None

    normalized = str(style_name).strip().lower()
    return normalized or None


def list_available_styles():
    """返回当前支持的风格名称列表。"""
    return tuple(STYLE_PRESETS.keys())


def get_style_preset(style_name):
    """返回解析后的风格名称、覆盖项及是否命中有效预设。"""
    normalized = normalize_style_name(style_name)

    if normalized is None:
        return DEFAULT_STYLE_NAME, STYLE_PRESETS[DEFAULT_STYLE_NAME], True

    if normalized in STYLE_PRESETS:
        return normalized, STYLE_PRESETS[normalized], True

    return DEFAULT_STYLE_NAME, STYLE_PRESETS[DEFAULT_STYLE_NAME], False