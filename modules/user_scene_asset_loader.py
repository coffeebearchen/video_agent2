# -*- coding: utf-8 -*-
"""
modules/user_scene_asset_loader.py

功能：
1. 只负责读取用户 scene 素材映射
2. 构建 scene_id -> asset_path 映射
3. 推断 asset_type
4. 检查文件是否存在
5. 返回安全结果

异常时返回空映射，不中断主链。
"""

import os
import json
from typing import Dict, Any, Optional

from modules import project_paths


# =========================
# 常量
# =========================

SUPPORTED_IMAGE_TYPES = {".png", ".jpg", ".jpeg", ".webp"}
SUPPORTED_VIDEO_TYPES = {".mp4", ".mov", ".mkv", ".webm"}


# =========================
# 核心逻辑
# =========================

def guess_asset_type_from_extension(file_path: Optional[str]) -> Optional[str]:
    """
    根据后缀推断 asset_type。
    返回：image / video / None
    """
    if not file_path:
        return None

    ext = os.path.splitext(str(file_path).lower())[1]
    if ext in SUPPORTED_IMAGE_TYPES:
        return "image"
    if ext in SUPPORTED_VIDEO_TYPES:
        return "video"
    return None


def resolve_user_asset_path(relative_path: Optional[str]) -> Optional[str]:
    """
    把相对路径转为项目绝对路径。
    如果本来就是绝对路径，则直接返回。
    """
    if not relative_path:
        return None

    path_str = str(relative_path).strip()
    if not path_str:
        return None

    if os.path.isabs(path_str):
        return path_str

    project_root = str(project_paths.get_project_root())
    return os.path.join(project_root, path_str)


def load_user_scene_asset_overrides() -> Dict[int, Dict[str, str]]:
    """
    读取用户素材映射，返回：
    {
        1: {"asset_path": "...", "asset_type": "video"},
        2: {"asset_path": "...", "asset_type": "image"},
        ...
    }

    异常时安全返回空映射。
    """
    result: Dict[int, Dict[str, str]] = {}

    override_path = str(project_paths.USER_SCENE_ASSET_OVERRIDE_PATH)
    if not os.path.exists(override_path):
        return result

    try:
        with open(override_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[USER_ASSET] 读取用户映射文件失败：{e}")
        return result

    # 安全解析 scene_asset_overrides
    overrides = data.get("scene_asset_overrides")
    if not isinstance(overrides, list):
        print(f"[USER_ASSET][WARN] scene_asset_overrides 不是 list，已忽略")
        return result

    for item in overrides:
        if not isinstance(item, dict):
            continue

        scene_id = item.get("scene_id")
        asset_path = item.get("asset_path")

        # 必要字段校验
        if scene_id is None or asset_path is None:
            continue

        try:
            scene_id = int(scene_id)
        except (ValueError, TypeError):
            continue

        # 路径转换
        resolved_path = resolve_user_asset_path(asset_path)
        if not resolved_path:
            continue

        # 文件存在性检查
        if not os.path.exists(resolved_path):
            print(f"[USER_ASSET][WARN] scene_id={scene_id} 文件不存在，已跳过：{asset_path}")
            continue

        # 类型推断
        asset_type = guess_asset_type_from_extension(resolved_path)
        if not asset_type:
            print(f"[USER_ASSET][WARN] scene_id={scene_id} 不支持的文件类型，已跳过：{asset_path}")
            continue

        # 成功录入
        result[scene_id] = {
            "asset_path": resolved_path,
            "asset_type": asset_type,
        }

    return result
