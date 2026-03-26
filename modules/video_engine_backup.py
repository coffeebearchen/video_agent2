# -*- coding: utf-8 -*-
"""
video_engine.py
========================================================
作用：
1. 接收已经生成好的图片列表
2. 按卡片类型设置时长
3. 使用 ImageSequenceClip 合成为 output/video.mp4
"""

import os
from typing import List, Dict

from moviepy.video.io.ImageSequenceClip import ImageSequenceClip


CARD_DURATIONS = {
    "hook": 3,
    "concept": 5,
    "analogy": 6,
    "example": 6,
    "insight": 4
}


def get_card_duration(card_type: str) -> int:
    return CARD_DURATIONS.get(card_type, 5)


def build_video_from_images(
    image_paths: List[str],
    cards: List[Dict],
    video_file: str,
    fps: int = 24
) -> None:
    if not image_paths:
        raise RuntimeError("没有可用图片，无法生成视频。")

    durations = []

    for i, image_path in enumerate(image_paths):
        if not os.path.exists(image_path):
            raise RuntimeError(f"找不到图片文件：{image_path}")

        card = cards[i] if i < len(cards) else {}
        card_type = card.get("type", "")
        duration = get_card_duration(card_type)
        durations.append(duration)

    parent = os.path.dirname(video_file)
    if parent:
        os.makedirs(parent, exist_ok=True)

    clip = None
    try:
        clip = ImageSequenceClip(image_paths, durations=durations)
        clip.write_videofile(
            video_file,
            fps=fps,
            codec="libx264",
            audio=False
        )
    finally:
        if clip is not None:
            try:
                clip.close()
            except Exception:
                pass