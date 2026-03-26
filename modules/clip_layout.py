# -*- coding: utf-8 -*-
"""
文件名：clip_layout.py
作用说明：
1. 负责视频 clip 的竖屏 cover 适配
2. 负责视频 clip 的时长裁切或循环补齐
3. 返回适合 video_builder 合成的背景 clip

本次改动点：
1. 补充 MoviePy 新旧版本导入兼容
2. 补充 clip 常用方法的新旧 API 兼容
3. 不改布局逻辑，只修当前运行环境兼容性
"""

import importlib


try:
    vfx = importlib.import_module("moviepy.editor").vfx
except ModuleNotFoundError:
    vfx = importlib.import_module("moviepy").vfx


def _set_duration(clip, duration):
    """兼容 MoviePy 新旧版本的时长设置方法。"""
    if hasattr(clip, "set_duration"):
        return clip.set_duration(duration)
    return clip.with_duration(duration)


def _resize_clip(clip, scale):
    """兼容 MoviePy 新旧版本的缩放方法。"""
    if hasattr(clip, "resize"):
        return clip.resize(scale)
    return clip.resized(scale)


def _crop_clip(clip, x_center, y_center, width, height):
    """兼容 MoviePy 新旧版本的裁切方法。"""
    if hasattr(clip, "crop"):
        return clip.crop(x_center=x_center, y_center=y_center, width=width, height=height)
    return clip.cropped(x_center=x_center, y_center=y_center, width=width, height=height)


def _subclip(clip, start_time, end_time):
    """兼容 MoviePy 新旧版本的截取方法。"""
    if hasattr(clip, "subclip"):
        return clip.subclip(start_time, end_time)
    return clip.subclipped(start_time, end_time)


def _loop_clip(clip, duration):
    """兼容 MoviePy 新旧版本的循环效果。"""
    if hasattr(clip, "fx") and hasattr(vfx, "loop"):
        return clip.fx(vfx.loop, duration=duration)
    return clip.with_effects([vfx.Loop(duration=duration)])


def _resize_and_crop_cover(clip, target_width, target_height):
    """按 cover 方式适配视频尺寸，保持比例并居中裁切。"""
    source_width, source_height = clip.size
    if source_width <= 0 or source_height <= 0:
        raise ValueError("视频尺寸无效，无法完成画面适配")

    scale = max(target_width / source_width, target_height / source_height)
    resized_clip = _resize_clip(clip, scale)
    resized_width, resized_height = resized_clip.size

    return _crop_clip(
        resized_clip,
        x_center=resized_width / 2,
        y_center=resized_height / 2,
        width=target_width,
        height=target_height,
    )


def _fit_duration(clip, duration):
    """将视频 clip 时长适配到 scene.duration。"""
    clip_duration = float(clip.duration or 0.0)
    if clip_duration <= 0:
        raise ValueError("视频时长无效，无法完成 scene 时长适配")

    if clip_duration > duration:
        fitted_clip = _subclip(clip, 0, duration)
        strategy = f"截取前 {duration:.2f} 秒"
    elif clip_duration < duration:
        fitted_clip = _loop_clip(clip, duration)
        strategy = f"循环补足到 {duration:.2f} 秒"
    else:
        fitted_clip = _set_duration(clip, duration)
        strategy = "时长刚好匹配"

    return _set_duration(fitted_clip, duration), strategy


def prepare_video_background_clip(video_clip, duration, width, height):
    """对视频 clip 做静音、时长适配和画面 cover 适配。"""
    silent_clip = video_clip.without_audio()
    duration_clip, strategy = _fit_duration(silent_clip, duration)
    fitted_clip = _resize_and_crop_cover(duration_clip, width, height)
    return _set_duration(fitted_clip, duration), strategy