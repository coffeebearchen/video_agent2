# -*- coding: utf-8 -*-
"""
image_layout.py

作用：
1. 负责背景图按比例缩放与居中裁切
2. 负责轻微整体暗化，提升信息卡片可读性
3. 输出适合 video_builder 使用的 numpy 背景数组

注意：
- 只处理画面层布局
- 不处理素材选择
- 不处理视频拼接
- 不修改任何主链数据结构
"""

import numpy as np
from PIL import Image

from modules.config import IMAGE_LAYOUT, ImageLayoutConfig


def _resize_cover(image, target_width, target_height, image_config=IMAGE_LAYOUT):
    """按 cover 方式缩放，保持比例并确保画布被填满。"""
    source_width, source_height = image.size
    if source_width <= 0 or source_height <= 0:
        raise ValueError("图片尺寸无效，无法完成画面适配")

    scale = max(target_width / source_width, target_height / source_height)
    resized_width = max(1, int(round(source_width * scale)))
    resized_height = max(1, int(round(source_height * scale)))

    resized_image = image.resize((resized_width, resized_height), image_config.resampling_mode)
    return resized_image


def _center_crop(image, target_width, target_height):
    """以中心区域为基准裁切到目标尺寸。"""
    current_width, current_height = image.size
    if current_width < target_width or current_height < target_height:
        raise ValueError("图片缩放后尺寸不足，无法完成居中裁切")

    left = max(0, (current_width - target_width) // 2)
    top = max(0, (current_height - target_height) // 2)
    right = left + target_width
    bottom = top + target_height

    return image.crop((left, top, right, bottom))


def _apply_dark_overlay(image, image_config=IMAGE_LAYOUT):
    """为整张背景图叠加轻微统一暗层。"""
    rgba_image = image.convert("RGBA")
    overlay = Image.new("RGBA", rgba_image.size, (0, 0, 0, image_config.dark_overlay_alpha))
    merged_image = Image.alpha_composite(rgba_image, overlay)
    return merged_image.convert("RGB")


def prepare_background_image(image_path, target_width, target_height, image_config: ImageLayoutConfig = IMAGE_LAYOUT):
    """读取图片并完成 cover 缩放、居中裁切、轻微暗化，返回 numpy 数组。"""
    with Image.open(image_path) as source_image:
        rgb_image = source_image.convert("RGB")
        resized_image = _resize_cover(rgb_image, target_width, target_height, image_config=image_config)
        cropped_image = _center_crop(resized_image, target_width, target_height)
        final_image = _apply_dark_overlay(cropped_image, image_config=image_config)

    return np.array(final_image)