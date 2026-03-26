# -*- coding: utf-8 -*-
"""
文件名：project_paths.py
作用说明：
1. 统一管理项目内的标准路径
2. 提供固定素材目录和索引文件路径
3. 避免各模块重复拼接路径

设计边界：
1. 只做路径定义与基础目录保障
2. 不做素材扫描和匹配逻辑
3. 不接入主链业务流程
"""

from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = PROJECT_ROOT / "assets"
DATA_DIR = PROJECT_ROOT / "data"
DATA_CURRENT_DIR = DATA_DIR / "current"

ASSETS_INSERTS_DIR = ASSETS_DIR / "inserts"
ASSETS_SYSTEM_IMAGES_DIR = ASSETS_DIR / "system_images"
ASSETS_SYSTEM_CLIPS_DIR = ASSETS_DIR / "system_clips"
ASSETS_USER_IMAGES_DIR = ASSETS_DIR / "user_images"
ASSETS_USER_CLIPS_DIR = ASSETS_DIR / "user_clips"

ASSET_INDEX_PATH = DATA_CURRENT_DIR / "asset_index.json"


def get_project_root():
    """返回项目根目录。"""
    return PROJECT_ROOT


def get_assets_dir():
    """返回素材根目录。"""
    return ASSETS_DIR


def get_data_current_dir():
    """返回 data/current 目录。"""
    return DATA_CURRENT_DIR


def get_asset_index_path():
    """返回标准素材索引文件路径。"""
    return ASSET_INDEX_PATH


def get_standard_asset_dirs():
    """返回 Task31 固定素材目录映射。"""
    return {
        "inserts": ASSETS_INSERTS_DIR,
        "system_images": ASSETS_SYSTEM_IMAGES_DIR,
        "system_clips": ASSETS_SYSTEM_CLIPS_DIR,
        "user_images": ASSETS_USER_IMAGES_DIR,
        "user_clips": ASSETS_USER_CLIPS_DIR,
    }


def ensure_standard_directories():
    """确保标准素材目录和 data/current 目录存在。"""
    created_paths = []

    for path in get_standard_asset_dirs().values():
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)
            created_paths.append(path)

    if not DATA_CURRENT_DIR.exists():
        DATA_CURRENT_DIR.mkdir(parents=True, exist_ok=True)
        created_paths.append(DATA_CURRENT_DIR)

    return created_paths


def to_project_relative_path(path_value):
    """将绝对路径转换为项目相对路径，并统一为 / 分隔。"""
    path_obj = Path(path_value).resolve()
    return path_obj.relative_to(PROJECT_ROOT).as_posix()
