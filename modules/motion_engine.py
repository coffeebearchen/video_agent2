# -*- coding: utf-8 -*-
"""
文件名：motion_engine.py
作用说明：
1. 定义背景图的明显运动模式
2. 为 video_builder 提供可直接使用的动态背景 clip
3. 保持运动稳定、平滑、可批量生成

本次改动点：
1. 补充 MoviePy 新旧版本导入兼容
2. 补充 ImageClip 常用方法的新旧 API 兼容
3. 不改运动策略，只修当前运行环境兼容性
"""

import hashlib
import importlib
import math

try:
    ImageClip = importlib.import_module("moviepy.editor").ImageClip
except ModuleNotFoundError:
    ImageClip = importlib.import_module("moviepy").ImageClip

from modules.config import MOTION, MotionConfig


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


def _resize_clip(clip, scale):
    """兼容 MoviePy 新旧版本的缩放方法。"""
    if hasattr(clip, "resize"):
        return clip.resize(scale)
    return clip.resized(scale)


def get_motion_canvas_size(frame_width, frame_height, motion_config: MotionConfig = MOTION):
    """返回为运动留出冗余空间的背景图尺寸。"""
    motion_width = max(frame_width, int(math.ceil(frame_width * motion_config.motion_canvas_scale)))
    motion_height = max(frame_height, int(math.ceil(frame_height * motion_config.motion_canvas_scale)))
    return motion_width, motion_height


def _ease_in_out(progress):
    """平滑缓动，避免运动生硬。"""
    clamped = min(max(progress, 0.0), 1.0)
    return clamped * clamped * (3.0 - 2.0 * clamped)


def choose_motion_mode(scene_index, scene_type, text, motion_config: MotionConfig = MOTION):
    """基于 scene 信息稳定选择一种运动模式，保证多次生成结果一致。"""
    seed_text = f"{scene_index}|{scene_type}|{text}".encode("utf-8", errors="ignore")
    digest = hashlib.md5(seed_text).hexdigest()
    mode_index = int(digest[:8], 16) % len(motion_config.motion_modes)
    return motion_config.motion_modes[mode_index]


def _build_pan_clip(background_array, duration, frame_width, frame_height, direction, motion_config):
    """构建平移类背景 clip。"""
    source_height, source_width = background_array.shape[:2]
    clip = _set_duration(ImageClip(background_array), duration)

    overflow_x = max(0, source_width - frame_width)
    overflow_y = max(0, source_height - frame_height)
    travel_x = overflow_x * motion_config.pan_travel_ratio
    travel_y = overflow_y * motion_config.pan_travel_ratio

    base_x = -max(0.0, (overflow_x - travel_x) / 2.0)
    base_y = -max(0.0, (overflow_y - travel_y) / 2.0)

    if direction == "pan_left_to_right":
        start_x = base_x
        end_x = base_x - travel_x
        start_y = end_y = -overflow_y / 2.0
    elif direction == "pan_right_to_left":
        start_x = base_x - travel_x
        end_x = base_x
        start_y = end_y = -overflow_y / 2.0
    elif direction == "pan_top_to_bottom":
        start_y = base_y
        end_y = base_y - travel_y
        start_x = end_x = -overflow_x / 2.0
    else:
        start_y = base_y - travel_y
        end_y = base_y
        start_x = end_x = -overflow_x / 2.0

    def position_at_time(t):
        progress = _ease_in_out(t / duration if duration > 0 else 1.0)
        current_x = start_x + (end_x - start_x) * progress
        current_y = start_y + (end_y - start_y) * progress
        return current_x, current_y

    return _set_position(clip, position_at_time)


def _build_zoom_clip(background_array, duration, direction, motion_config):
    """构建缩放类背景 clip。"""
    clip = _set_duration(ImageClip(background_array), duration)

    if direction == "zoom_in":
        start_scale = motion_config.zoom_in_start_scale
        end_scale = motion_config.zoom_in_end_scale
    else:
        start_scale = motion_config.zoom_out_start_scale
        end_scale = motion_config.zoom_out_end_scale

    def scale_at_time(t):
        progress = _ease_in_out(t / duration if duration > 0 else 1.0)
        return start_scale + (end_scale - start_scale) * progress

    resized_clip = _resize_clip(clip, scale_at_time)
    return _set_position(resized_clip, "center")


def build_motion_background_clip(
    background_array,
    duration,
    frame_width,
    frame_height,
    motion_mode,
    motion_config: MotionConfig = MOTION,
):
    """根据指定运动模式生成背景 clip。"""
    if motion_mode in {"zoom_in", "zoom_out"}:
        return _build_zoom_clip(background_array, duration, motion_mode, motion_config)

    return _build_pan_clip(background_array, duration, frame_width, frame_height, motion_mode, motion_config)