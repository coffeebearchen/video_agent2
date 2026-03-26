# -*- coding: utf-8 -*-
"""
asset_manager.py

作用：
1. 根据 scene_type 映射到固定素材目录
2. 优先从 assets/videos 下选择视频 clip
3. 若无视频，再从 assets/images 下选择图片
4. 当目录不存在、为空、类型未识别或无可用素材时，返回 None

注意：
- 只做最小素材路径选择
- 不做素材匹配打分
- 不做复杂策略
"""

import random
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
IMAGES_ROOT_DIR = BASE_DIR / "assets" / "images"
VIDEOS_ROOT_DIR = BASE_DIR / "assets" / "videos"
SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
SUPPORTED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v"}
SCENE_TYPE_MAP = {
    "overlay": "intro",
    "explain": "body",
    "card": "outro",
    "intro": "intro",
    "body": "body",
    "outro": "outro",
}


def _normalize_scene_type(scene_type: str):
    normalized_type = str(scene_type or "").strip().lower()
    target_dir_name = SCENE_TYPE_MAP.get(normalized_type)
    return normalized_type, target_dir_name


def _collect_files(target_dir: Path, supported_extensions):
    if not target_dir.exists():
        return None, "目录不存在"

    if not target_dir.is_dir():
        return None, "路径不是目录"

    asset_files = [
        file_path for file_path in target_dir.iterdir()
        if file_path.is_file() and file_path.suffix.lower() in supported_extensions
    ]

    if not asset_files:
        return [], "目录为空"

    return asset_files, "可用"


def get_video_for_scene(scene_type: str):
    """根据 scene_type 返回一条可用视频路径，失败时返回 None。"""
    normalized_type, target_dir_name = _normalize_scene_type(scene_type)

    if not target_dir_name:
        print(f"[asset_manager] 未识别的 scene_type: {scene_type}，无法选择视频素材")
        return None

    video_dir = VIDEOS_ROOT_DIR / target_dir_name
    video_files, video_status = _collect_files(video_dir, SUPPORTED_VIDEO_EXTENSIONS)
    if video_files:
        selected_video = random.choice(video_files)
        relative_path = selected_video.relative_to(BASE_DIR)
        print(f"[asset_manager] scene_type={normalized_type} -> 命中视频素材: {relative_path}")
        return selected_video

    print(f"[asset_manager] 视频目录{video_status}: {video_dir}")
    return None


def get_image_for_scene(scene_type: str):
    """根据 scene_type 返回一张可用图片路径，失败时返回 None。"""
    normalized_type, target_dir_name = _normalize_scene_type(scene_type)

    if not target_dir_name:
        print(f"[asset_manager] 未识别的 scene_type: {scene_type}，无法选择图片素材")
        return None

    image_dir = IMAGES_ROOT_DIR / target_dir_name
    image_files, image_status = _collect_files(image_dir, SUPPORTED_IMAGE_EXTENSIONS)
    if image_files:
        selected_image = random.choice(image_files)
        relative_path = selected_image.relative_to(BASE_DIR)
        print(f"[asset_manager] scene_type={normalized_type} -> 命中图片素材: {relative_path}")
        return selected_image

    print(f"[asset_manager] 图片目录{image_status}: {image_dir}")
    return None


def get_background_asset_for_scene(scene_type: str):
    """根据 scene_type 返回背景素材信息，优先视频，其次图片。"""
    normalized_type, target_dir_name = _normalize_scene_type(scene_type)

    if not target_dir_name:
        print(f"[asset_manager] 未识别的 scene_type: {scene_type}，使用 fallback 纯色背景")
        return None

    video_path = get_video_for_scene(scene_type)
    if video_path is not None:
        return {
            "asset_type": "video",
            "asset_path": video_path,
        }

    image_path = get_image_for_scene(scene_type)
    if image_path is not None:
        print(f"[asset_manager] scene_type={normalized_type} -> 回退使用图片素材")
        return {
            "asset_type": "image",
            "asset_path": image_path,
        }

    print(f"[asset_manager] scene_type={normalized_type} 无可用视频或图片，使用 fallback 纯色背景")
    return None
