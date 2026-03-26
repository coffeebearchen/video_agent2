# -*- coding: utf-8 -*-
"""
文件名：asset_registry.py
作用说明：
1. 扫描标准素材目录
2. 生成最小稳定素材索引
3. 提供索引保存与读取能力

设计边界：
1. 只处理固定目录和固定文件类型
2. 不做智能匹配、不做标签推理
3. 不接入 scene/render 主链
"""

from __future__ import annotations

from datetime import datetime
import json

from modules.project_paths import (
    get_assets_dir,
    get_asset_index_path,
    get_standard_asset_dirs,
    ensure_standard_directories,
    to_project_relative_path,
)


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}
DEFAULT_INSERT_PATH = "assets/inserts/default.png"
DEFAULT_INSERT_NOTE = "default.png 为兼容性补齐默认素材入口，不代表正式素材策略结论"

ASSET_TYPE_BY_DIRECTORY = {
    "inserts": "image",
    "system_images": "image",
    "system_clips": "video",
    "user_images": "image",
    "user_clips": "video",
}


def _get_allowed_extensions(asset_type):
    """按素材类型返回允许扩展名集合。"""
    if asset_type == "image":
        return IMAGE_EXTENSIONS
    if asset_type == "video":
        return VIDEO_EXTENSIONS
    return set()


def _build_asset_id(directory_key, index):
    """生成稳定可读的 asset_id。"""
    return f"{directory_key}_{index:03d}"


def _build_asset_record(file_path, directory_key, asset_type, index):
    """构造单条素材记录。"""
    return {
        "asset_id": _build_asset_id(directory_key, index),
        "category": directory_key,
        "type": asset_type,
        "file_name": file_path.name,
        "path": to_project_relative_path(file_path),
        "enabled": True,
    }


def scan_standard_assets():
    """扫描固定素材目录，并返回素材列表与日志。"""
    created_paths = ensure_standard_directories()
    logs = []
    assets = []
    summary = {}

    if created_paths:
        for created_path in created_paths:
            logs.append(f"已创建目录：{created_path}")

    for directory_key, directory_path in get_standard_asset_dirs().items():
        logs.append(f"开始扫描分类：{directory_key}")
        asset_type = ASSET_TYPE_BY_DIRECTORY[directory_key]
        allowed_extensions = _get_allowed_extensions(asset_type)
        summary[directory_key] = {
            "count": 0,
            "ignored": 0,
        }

        files = sorted(
            [item for item in directory_path.iterdir() if item.is_file()],
            key=lambda item: item.name.lower(),
        )

        record_index = 0
        for file_path in files:
            suffix = file_path.suffix.lower()
            if suffix not in allowed_extensions:
                summary[directory_key]["ignored"] += 1
                logs.append(
                    f"已忽略非法后缀文件：{to_project_relative_path(file_path)}"
                )
                continue

            record_index += 1
            record = _build_asset_record(
                file_path=file_path,
                directory_key=directory_key,
                asset_type=asset_type,
                index=record_index,
            )
            assets.append(record)
            summary[directory_key]["count"] += 1

        logs.append(
            f"{directory_key} 扫描完成：{summary[directory_key]['count']} 个素材"
        )

    return {
        "assets": assets,
        "summary": summary,
        "logs": logs,
    }


def save_asset_index(index_data, output_path=None):
    """保存标准素材索引文件。"""
    target_path = output_path or get_asset_index_path()
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with open(target_path, "w", encoding="utf-8") as file:
        json.dump(index_data, file, ensure_ascii=False, indent=2)

    return target_path


def load_asset_index(index_path=None):
    """读取标准素材索引文件。"""
    target_path = index_path or get_asset_index_path()
    if not target_path.exists():
        raise FileNotFoundError(f"asset_index.json 不存在：{target_path}")

    with open(target_path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("asset_index.json 格式错误，必须为对象结构")

    if not isinstance(data.get("assets", []), list):
        raise ValueError("asset_index.json 格式错误，assets 必须为数组")

    return data


def build_asset_index():
    """扫描并生成标准素材索引。"""
    scan_result = scan_standard_assets()
    counts = {
        category: item.get("count", 0)
        for category, item in scan_result["summary"].items()
    }
    meta = {}
    if any(asset.get("path") == DEFAULT_INSERT_PATH for asset in scan_result["assets"]):
        meta["default_insert_note"] = DEFAULT_INSERT_NOTE

    index_data = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "base_dir": to_project_relative_path(get_assets_dir()),
        "counts": counts,
        "assets": scan_result["assets"],
    }
    if meta:
        index_data["meta"] = meta

    output_path = save_asset_index(index_data)
    scan_result["logs"].append(f"已生成素材索引：{output_path}")

    return {
        "index": index_data,
        "summary": scan_result["summary"],
        "output_path": output_path,
        "logs": scan_result["logs"],
    }
