# -*- coding: utf-8 -*-
"""
文件名：config.py
作用说明：
1. 提供默认参数定义
2. 提供默认参数与风格预设的合并逻辑
3. 构造整条视频级别的运行时配置
4. 为表达模块提供统一开关与默认参数

本次改动点：
1. 新增表达模块配置结构
2. 为 segment 动画补开关位
3. 为关键词高亮补开关位
4. 为关键词强调动画补开关位与默认参数
"""

from dataclasses import dataclass, fields, replace
from pathlib import Path

from PIL import Image

from modules.style_presets import DEFAULT_STYLE_NAME, get_style_preset


PROJECT_ROOT = Path(__file__).resolve().parent.parent


@dataclass(frozen=True)
class VideoConfig:
    width: int = 1080
    height: int = 1920
    fps: int = 24
    default_duration: float = 4.0
    background_color: tuple[int, int, int] = (18, 18, 22)


@dataclass(frozen=True)
class TransitionConfig:
    default_fade_duration: float = 0.45
    soft_min_fade_duration: float = 0.28
    hard_min_fade_duration: float = 0.18
    base_fade_ratio: float = 0.15
    max_fade_ratio: float = 0.33


@dataclass(frozen=True)
class StyleTransitionConfig:
    """style 层的全局转场配置。

    第一版只暴露最小可控字段：
    1. enabled: 是否开启全局转场
    2. type: 当前只读取 fade，其他值交由 video_builder 回退
    3. duration: fade 时长，默认 0.5 秒
    """

    enabled: bool = True
    type: str = "fade"
    duration: float = 0.5


@dataclass(frozen=True)
class UICardConfig:
    label_text: str = "VIDEO AGENT"
    card_width_ratio: float = 0.87
    card_top_ratio: float = 0.66
    card_max_height_ratio: float = 0.34
    card_bottom_margin: int = 96
    card_radius: int = 30
    card_border_width: int = 2
    card_fill: tuple[int, int, int, int] = (12, 12, 16, 176)
    card_border: tuple[int, int, int, int] = (255, 255, 255, 46)
    title_color: tuple[int, int, int, int] = (208, 213, 221, 255)
    text_color: tuple[int, int, int, int] = (255, 255, 255, 255)
    text_font_size: int = 60
    label_font_size: int = 28
    text_line_spacing: int = 18
    label_text_gap: int = 24
    padding_x: int = 52
    padding_top: int = 34
    padding_bottom: int = 40
    max_lines: int = 6
    windows_font_candidates: tuple[str, ...] = (
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    )
    project_font_candidates: tuple[str, ...] = (
        "fonts/SourceHanSansSC-Regular.otf",
        "fonts/SourceHanSansCN-Bold.otf",
    )


@dataclass(frozen=True)
class ImageLayoutConfig:
    dark_overlay_alpha: int = 44
    resampling_mode: Image.Resampling = Image.Resampling.LANCZOS


@dataclass(frozen=True)
class MotionConfig:
    motion_canvas_scale: float = 1.22
    pan_travel_ratio: float = 0.72
    zoom_in_start_scale: float = 1.0
    zoom_in_end_scale: float = 1.16
    zoom_out_start_scale: float = 1.16
    zoom_out_end_scale: float = 1.0
    motion_modes: tuple[str, ...] = (
        "zoom_in",
        "zoom_out",
        "pan_left_to_right",
        "pan_right_to_left",
        "pan_top_to_bottom",
        "pan_bottom_to_top",
    )


@dataclass(frozen=True)
class ExpressionModulesConfig:
    """表达模块统一开关配置。

    默认策略：
    1. segment 进入动画默认开启，保持 Task15 既有体验。
    2. 关键词高亮默认开启，保持 Task16 既有体验。
    3. 关键词强调默认开启，但强度保持轻量，避免破坏排版。
    """

    segment_animation_enabled: bool = True
    highlight_enabled: bool = True
    highlight_emphasis_enabled: bool = True
    default_segment_animation: str = "fade_in"
    default_highlight_animation: str = "pop"
    highlight_emphasis_strength: float = 0.12


@dataclass(frozen=True)
class VisualInsertConfig:
    """中间视觉插入层配置。

    支持在 scene 内插入图片、图卡等中间视觉素材。
    
    默认策略：
    1. visual_insert 功能默认开启
    2. 默认缩放 0.72（占视频宽度 72%）
    3. 默认位置 center（居中）
    4. 淡入效果时长 0.18 秒，与 transition 的 hard_min_fade_duration 对齐
    """

    visual_insert_enabled: bool = True
    visual_insert_default_scale: float = 0.72
    visual_insert_default_position: str = "center"
    visual_insert_default_fade_duration: float = 0.18


@dataclass(frozen=True)
class TemplateConfig:
	"""
	模板系统配置。
	
	在 TASK20-A 中新增。
	用于控制模板系统的启用开关与默认模板选择。
	
	字段说明：
	- template_enabled: 模板系统是否启用
	  - True（默认）：启用模板 fallback 机制
	  - False：禁用所有模板 fallback，使用风格/运行时默认值
	- template_name: 当前使用的模板名称（若启用了模板系统）
	"""
	template_enabled: bool = True
	template_name: str | None = None


@dataclass(frozen=True)
class RuntimeConfig:
    style_name: str
    requested_style: str | None
    style_found: bool
    template: TemplateConfig
    video: VideoConfig
    transition: TransitionConfig
    style_transition: StyleTransitionConfig
    ui_card: UICardConfig
    image_layout: ImageLayoutConfig
    motion: MotionConfig
    expression_modules: ExpressionModulesConfig
    visual_insert: VisualInsertConfig


VIDEO = VideoConfig()
TRANSITION = TransitionConfig()
STYLE_TRANSITION = StyleTransitionConfig()
UI_CARD = UICardConfig()
IMAGE_LAYOUT = ImageLayoutConfig()
MOTION = MotionConfig()
EXPRESSION_MODULES = ExpressionModulesConfig()
VISUAL_INSERT = VisualInsertConfig()
TEMPLATE = TemplateConfig()


def _apply_overrides(base_config, overrides):
    """将覆盖参数安全合并到 dataclass 配置中。"""
    if not overrides:
        return base_config

    valid_field_names = {item.name for item in fields(base_config)}
    filtered_overrides = {key: value for key, value in overrides.items() if key in valid_field_names}
    if not filtered_overrides:
        return base_config

    return replace(base_config, **filtered_overrides)


def _coerce_bool(value, default_value):
    """将输入值稳定转换为布尔值。"""
    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True
        if normalized in {"false", "0", "no", "off"}:
            return False

    return default_value


def _build_style_transition_config(preset_overrides, transition_config, style_overrides=None):
    """构建 style 层转场配置，并保留旧 transition 作为兼容回退来源。"""
    preset_transition_overrides = preset_overrides.get("style_transition")
    if not isinstance(preset_transition_overrides, dict):
        preset_transition_overrides = {}

    style_transition_overrides = {}
    if isinstance(style_overrides, dict):
        style_transition_candidate = style_overrides.get("transition")
        if isinstance(style_transition_candidate, dict):
            style_transition_overrides = style_transition_candidate

    compatibility_duration = transition_config.default_fade_duration
    if not isinstance(compatibility_duration, (int, float)) or compatibility_duration <= 0:
        compatibility_duration = STYLE_TRANSITION.duration

    enabled_value = style_transition_overrides.get(
        "enabled",
        preset_transition_overrides.get("enabled", STYLE_TRANSITION.enabled),
    )
    type_value = style_transition_overrides.get(
        "type",
        preset_transition_overrides.get("type", STYLE_TRANSITION.type),
    )
    duration_value = style_transition_overrides.get(
        "duration",
        preset_transition_overrides.get("duration", compatibility_duration),
    )

    resolved_type = str(type_value or STYLE_TRANSITION.type).strip().lower() or STYLE_TRANSITION.type
    try:
        resolved_duration = float(duration_value)
    except (TypeError, ValueError):
        resolved_duration = STYLE_TRANSITION.duration

    if resolved_duration <= 0:
        resolved_duration = STYLE_TRANSITION.duration

    return StyleTransitionConfig(
        enabled=_coerce_bool(enabled_value, STYLE_TRANSITION.enabled),
        type=resolved_type,
        duration=resolved_duration,
    )


def build_runtime_config(style_name=None, template_name=None, template_enabled=True, style_overrides=None):
    """
    基于默认参数、风格预设、模板信息构建最终运行时配置。

    参数：
    - style_name: 风格名称（可选）
    - template_name: 模板名称（可选）
    - template_enabled: 是否启用模板系统（默认 True）
    - style_overrides: style 层额外覆盖项（可选），当前主要用于接收 style.transition

    返回：
    - RuntimeConfig，完整的运行时配置对象
    """
    resolved_style_name, preset_overrides, style_found = get_style_preset(style_name)

    runtime_video = _apply_overrides(VIDEO, preset_overrides.get("video"))
    runtime_transition = _apply_overrides(TRANSITION, preset_overrides.get("transition"))
    runtime_style_transition = _build_style_transition_config(
        preset_overrides,
        runtime_transition,
        style_overrides=style_overrides,
    )
    runtime_ui_card = _apply_overrides(UI_CARD, preset_overrides.get("ui_card"))
    runtime_image_layout = _apply_overrides(IMAGE_LAYOUT, preset_overrides.get("image_layout"))
    runtime_motion = _apply_overrides(MOTION, preset_overrides.get("motion"))
    runtime_expression_modules = _apply_overrides(EXPRESSION_MODULES, preset_overrides.get("expression_modules"))
    runtime_visual_insert = _apply_overrides(VISUAL_INSERT, preset_overrides.get("visual_insert"))

    requested_style = None if style_name is None else str(style_name).strip().lower() or None

    # 处理模板配置
    resolved_template_name = None
    if template_enabled and template_name:
        resolved_template_name = str(template_name).strip().lower() or None

    runtime_template = TemplateConfig(
        template_enabled=template_enabled,
        template_name=resolved_template_name,
    )

    return RuntimeConfig(
        style_name=resolved_style_name,
        requested_style=requested_style,
        style_found=style_found,
        template=runtime_template,
        video=runtime_video,
        transition=runtime_transition,
        style_transition=runtime_style_transition,
        ui_card=runtime_ui_card,
        image_layout=runtime_image_layout,
        motion=runtime_motion,
        expression_modules=runtime_expression_modules,
        visual_insert=runtime_visual_insert,
    )


DEFAULT_RUNTIME_CONFIG = build_runtime_config(DEFAULT_STYLE_NAME)