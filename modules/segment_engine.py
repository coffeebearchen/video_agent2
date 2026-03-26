# -*- coding: utf-8 -*-
"""
文件名：segment_engine.py
作用说明：
1. 负责读取并清洗 scene 内的 segments
2. 负责把 segment 文本渲染为带 start / duration 的 UI overlay clip
3. 在没有合法 segments 时回退为整段 scene.text 单卡片
4. 负责按配置控制 segment 进入动画是否启用

本次改动点：
1. 补充 MoviePy 新旧版本导入兼容
2. 补充 overlay clip 常用方法的新旧 API 兼容
3. 不改表达模块策略，只修当前运行环境兼容性
"""

import numpy as np
import importlib

try:
    _moviepy_module = importlib.import_module("moviepy.editor")
except ModuleNotFoundError:
    _moviepy_module = importlib.import_module("moviepy")

ImageClip = _moviepy_module.ImageClip
vfx = _moviepy_module.vfx

from modules.ui_renderer import normalize_highlights, render_info_card_with_config
from modules.template_presets import (
	get_template_role_defaults,
	validate_template_role,
)


def _set_duration(clip, duration):
    """兼容 MoviePy 新旧版本的时长设置方法。"""
    if hasattr(clip, "set_duration"):
        return clip.set_duration(duration)
    return clip.with_duration(duration)


def _set_position(clip, position):
    """兼容 MoviePy 新旧版本的位置设置方法。"""
    if hasattr(clip, "set_position"):
        return clip.set_position(position)
    return clip.with_position(position)


def _set_start(clip, start_time):
    """兼容 MoviePy 新旧版本的起始时间设置方法。"""
    if hasattr(clip, "set_start"):
        return clip.set_start(start_time)
    return clip.with_start(start_time)


def _resize_clip(clip, scale):
    """兼容 MoviePy 新旧版本的缩放方法。"""
    if hasattr(clip, "resize"):
        return clip.resize(scale)
    return clip.resized(scale)


def _apply_fadein(clip, duration):
    """兼容 MoviePy 新旧版本的淡入效果。"""
    if hasattr(clip, "fx") and hasattr(vfx, "fadein"):
        return clip.fx(vfx.fadein, duration)
    return clip.with_effects([vfx.FadeIn(duration)])


def get_allowed_segment_animations():
    """返回允许的 segment 动画列表。"""
    return ("fade_in", "slide_up", "zoom_in")


def get_allowed_highlight_animations():
    """返回允许的关键词强调动画列表。"""
    return ("pop", "none")


def get_default_segment_animation(runtime_config=None):
    """返回默认 segment 进入动画。"""
    expression_config = getattr(runtime_config, "expression_modules", None)
    default_animation = getattr(expression_config, "default_segment_animation", "fade_in")
    normalized = str(default_animation or "").strip().lower()
    if normalized in get_allowed_segment_animations():
        return normalized
    return "fade_in"


def get_default_highlight_animation(runtime_config=None):
    """返回默认关键词强调动画。"""
    expression_config = getattr(runtime_config, "expression_modules", None)
    default_animation = getattr(expression_config, "default_highlight_animation", "pop")
    normalized = str(default_animation or "").strip().lower()
    if normalized in get_allowed_highlight_animations():
        return normalized
    return "pop"


def should_enable_segment_animation(runtime_config=None):
    """根据表达模块配置决定是否启用 segment 进入动画。"""
    expression_config = getattr(runtime_config, "expression_modules", None)
    return bool(getattr(expression_config, "segment_animation_enabled", True))


def get_template_fallback_animation(scene, runtime_config=None):
	"""
	从模板中读取 scene 的默认动画类型。
	
	仅在以下条件全部满足时进行读取：
	1. runtime_config.template.template_enabled = True
	2. scene 有 template_role 字段且非空
	3. runtime_config.template.template_name 存在
	4. template_role 在该模板中有效
	
	参数：
	- scene: scene dict
	- runtime_config: RuntimeConfig
	
	返回：
	- str（动画类型）或 None
	"""
	# 检查模板系统是否启用
	if not runtime_config or not getattr(runtime_config, "template", None):
		return None
	
	if not runtime_config.template.template_enabled:
		return None
	
	template_name = runtime_config.template.template_name
	if not template_name:
		return None
	
	# 检查 scene 是否有 template_role
	if not isinstance(scene, dict):
		return None
	
	template_role = str(scene.get("template_role", "")).strip().lower()
	if not template_role:
		return None
	
	# 校验 template_role（打印 warning 但不报错）
	if not validate_template_role(template_name, template_role, warn=True):
		return None
	
	# 从模板获取默认值
	try:
		role_defaults = get_template_role_defaults(template_name, template_role)
		anim_enabled = role_defaults.get("segment_animation_enabled")
		if anim_enabled is False:
			return None
		return role_defaults.get("segment_animation")
	except Exception:
		return None


def get_segment_animation_duration(segment_duration):
    """返回 segment 进入动画时长。"""
    return min(0.35, max(0.12, segment_duration * 0.4))


def _ease_out(progress):
    """轻量缓动函数，让进入动画更自然。"""
    clamped = min(max(progress, 0.0), 1.0)
    return 1.0 - (1.0 - clamped) * (1.0 - clamped)


def _normalize_animation_name(animation_name, runtime_config=None, scene=None):
    """清洗并校验 animation 字段。"""
    normalized = str(animation_name or "").strip().lower()
    if normalized in get_allowed_segment_animations():
        return normalized
    
    # 如果没有明确指定动画，尝试从模板获取 fallback
    if not animation_name and scene and runtime_config:
        template_anim = get_template_fallback_animation(scene, runtime_config)
        if template_anim:
            return template_anim
    
    # 最后才用 runtime_config 的默认值
    return get_default_segment_animation(runtime_config)


def normalize_highlight_animation_name(animation_name, runtime_config=None):
    """清洗并校验 highlight_animation 字段。"""
    normalized = str(animation_name or "").strip().lower()
    if normalized in get_allowed_highlight_animations():
        return normalized
    return get_default_highlight_animation(runtime_config)


def _extract_card_image_and_position(rendered_image):
    """从全屏透明卡片图中提取实际卡片区域与最终位置。"""
    alpha_channel = rendered_image.getchannel("A")
    bbox = alpha_channel.getbbox()
    if not bbox:
        width, height = rendered_image.size
        return rendered_image, (0, 0), (width, height)

    cropped_image = rendered_image.crop(bbox)
    final_position = (bbox[0], bbox[1])
    card_size = (bbox[2] - bbox[0], bbox[3] - bbox[1])
    return cropped_image, final_position, card_size


def _to_float(value, default=None):
    """安全转换数字，失败时返回默认值。"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_segments(scene, scene_duration, runtime_config=None):
    """读取并清洗 scene.segments，返回合法 segment 列表。"""
    if not isinstance(scene, dict):
        return []

    raw_segments = scene.get("segments")
    if not isinstance(raw_segments, list):
        return []

    scene_highlight_animation = normalize_highlight_animation_name(
        scene.get("highlight_animation"),
        runtime_config,
    )

    normalized_segments = []
    for item in raw_segments:
        if not isinstance(item, dict):
            continue

        start = _to_float(item.get("start"), default=None)
        end = _to_float(item.get("end"), default=None)
        text = str(item.get("text", "") or "").strip()

        if start is None or end is None or not text:
            continue

        start = max(0.0, start)
        end = min(scene_duration, end)

        if end <= start:
            continue

        highlight_animation = item.get("highlight_animation", scene_highlight_animation)
        normalized_segments.append(
            {
                "start": start,
                "end": end,
                "text": text,
                "animation": _normalize_animation_name(item.get("animation"), runtime_config, scene),
                "highlights": normalize_highlights(item.get("highlights")),
                "highlight_animation": normalize_highlight_animation_name(highlight_animation, runtime_config),
            }
        )

    normalized_segments.sort(key=lambda item: (item["start"], item["end"]))
    return normalized_segments


def apply_fade_in_animation(base_clip, animation_duration, final_position):
    """实现淡入进入动画。"""
    return _apply_fadein(_set_position(base_clip, final_position), animation_duration)


def apply_slide_up_animation(base_clip, animation_duration, final_position):
    """实现轻微上滑进入动画。"""
    final_x, final_y = final_position
    start_offset_y = 56

    def position_at_time(t):
        if animation_duration <= 0:
            return final_x, final_y

        progress = _ease_out(t / animation_duration)
        current_y = final_y + start_offset_y * (1.0 - progress)
        return final_x, current_y

    return _apply_fadein(_set_position(base_clip, position_at_time), min(animation_duration, 0.18))


def apply_zoom_in_animation(base_clip, animation_duration, final_position):
    """实现轻微缩放进入动画。"""
    final_x, final_y = final_position
    base_width, base_height = base_clip.size
    start_scale = 0.94
    end_scale = 1.0

    def scale_at_time(t):
        if animation_duration <= 0:
            return end_scale

        progress = _ease_out(t / animation_duration)
        return start_scale + (end_scale - start_scale) * progress

    def position_at_time(t):
        current_scale = scale_at_time(t)
        current_width = base_width * current_scale
        current_height = base_height * current_scale
        current_x = final_x + (base_width - current_width) / 2.0
        current_y = final_y + (base_height - current_height) / 2.0
        return current_x, current_y

    animated_clip = _resize_clip(base_clip, scale_at_time)
    return _apply_fadein(_set_position(animated_clip, position_at_time), min(animation_duration, 0.16))


def apply_segment_animation(base_clip, animation_name, animation_duration, final_position, runtime_config=None):
    """根据动画名称为 segment 卡片应用进入动画。"""
    if not should_enable_segment_animation(runtime_config):
        return _set_position(base_clip, final_position)

    normalized_name = _normalize_animation_name(animation_name, runtime_config)

    if normalized_name == "slide_up":
        return apply_slide_up_animation(base_clip, animation_duration, final_position)

    if normalized_name == "zoom_in":
        return apply_zoom_in_animation(base_clip, animation_duration, final_position)

    return apply_fade_in_animation(base_clip, animation_duration, final_position)


def build_segment_text_clip(
    text,
    start,
    end,
    width,
    height,
    runtime_config,
    animation_name=None,
    highlights=None,
    highlight_animation=None,
):
    """构建单个 segment 的信息卡片 overlay clip，并应用进入动画。"""
    rendered_image = render_info_card_with_config(
        text=text,
        width=width,
        height=height,
        ui_config=runtime_config.ui_card,
        highlights=normalize_highlights(highlights),
        highlight_animation=normalize_highlight_animation_name(highlight_animation, runtime_config),
        expression_config=runtime_config.expression_modules,
    )

    card_image, final_position, _ = _extract_card_image_and_position(rendered_image)
    segment_duration = end - start
    animation_duration = get_segment_animation_duration(segment_duration)

    base_clip = _set_duration(ImageClip(np.array(card_image)), segment_duration)
    animated_clip = apply_segment_animation(
        base_clip=base_clip,
        animation_name=animation_name,
        animation_duration=animation_duration,
        final_position=final_position,
        runtime_config=runtime_config,
    )

    animated_clip = _set_start(animated_clip, start)
    return _set_duration(animated_clip, segment_duration)


def build_segment_overlay_clips(scene, scene_duration, width, height, runtime_config):
    """根据 scene 构建一个或多个 UI overlay clip。"""
    normalized_segments = normalize_segments(scene, scene_duration, runtime_config)
    if normalized_segments:
        overlay_clips = []
        for segment in normalized_segments:
            overlay_clip = build_segment_text_clip(
                text=segment["text"],
                start=segment["start"],
                end=segment["end"],
                width=width,
                height=height,
                runtime_config=runtime_config,
                animation_name=segment["animation"],
                highlights=segment["highlights"],
                highlight_animation=segment["highlight_animation"],
            )
            overlay_clips.append(overlay_clip)
        return overlay_clips

    fallback_text = ""
    fallback_highlights = []
    fallback_highlight_animation = get_default_highlight_animation(runtime_config)
    if isinstance(scene, dict):
        fallback_text = str(scene.get("text", "") or "").strip()
        fallback_highlights = normalize_highlights(scene.get("highlights"))
        fallback_highlight_animation = normalize_highlight_animation_name(
            scene.get("highlight_animation"),
            runtime_config,
        )

    if not fallback_text:
        fallback_text = " "

    return [
        build_segment_text_clip(
            text=fallback_text,
            start=0.0,
            end=scene_duration,
            width=width,
            height=height,
            runtime_config=runtime_config,
            animation_name=get_default_segment_animation(runtime_config),
            highlights=fallback_highlights,
            highlight_animation=fallback_highlight_animation,
        )
    ]