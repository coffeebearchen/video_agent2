# -*- coding: utf-8 -*-
"""
modules/asset_indexer.py

第一版素材索引生成器（可单独运行测试）

功能：
1. 扫描 assets/intro、assets/hook、assets/explain
2. 自动识别图片 / 视频
3. 自动推断 section
4. 生成 data/current/asset_index.json
5. 支持单文件直接运行测试

运行方式（推荐始终在项目根目录运行）：
    cd E:\video_agent
    python modules/asset_indexer.py

后续主链中调用方式：
    from modules.asset_indexer import build_asset_index
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List


# =========================
# 路径工具
# =========================

def get_project_root() -> str:
    """
    获取项目根目录。
    当前文件在 video_agent/modules/asset_indexer.py
    所以向上一级就是 video_agent 根目录。
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_assets_dir() -> str:
    """
    默认素材根目录：
    video_agent/assets
    """
    return os.path.join(get_project_root(), "assets")


def get_output_json_path() -> str:
    """
    默认输出 JSON：
    video_agent/data/current/asset_index.json
    """
    return os.path.join(get_project_root(), "data", "current", "asset_index.json")


# =========================
# 文件类型识别
# =========================

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}


def infer_type_from_ext(file_path: str) -> str:
    """
    根据扩展名识别文件类型。
    返回：
    - image
    - video
    - unknown
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    return "unknown"


def is_supported_asset(file_path: str) -> bool:
    """
    判断是否为支持的素材类型。
    """
    return infer_type_from_ext(file_path) in {"image", "video"}


# =========================
# section 推断
# =========================

def normalize_path(path_str: str) -> str:
    """
    路径统一成小写，并把反斜杠转成正斜杠，便于判断。
    """
    return path_str.replace("\\", "/").lower()


def infer_section_from_path(file_path: str) -> str:
    """
    从路径中推断 section。
    """
    path_norm = normalize_path(file_path)

    if "/intro/" in path_norm:
        return "intro"
    if "/hook/" in path_norm:
        return "hook"
    if "/explain/" in path_norm:
        return "explain"

    return "unknown"


# =========================
# asset_id 生成
# =========================

def build_asset_id(section: str, asset_type: str, counter: int) -> str:
    """
    生成 asset_id，例如：
    hook_img_001
    explain_vid_003
    """
    type_short = "img" if asset_type == "image" else "vid" if asset_type == "video" else "unk"
    return f"{section}_{type_short}_{counter:03d}"


# =========================
# 单条素材构建
# =========================

def to_relative_path(abs_path: str, root_dir: str) -> str:
    """
    把绝对路径转成相对于项目根目录的路径，并统一使用 /
    """
    rel_path = os.path.relpath(abs_path, root_dir)
    return rel_path.replace("\\", "/")


def build_asset_record(
    abs_path: str,
    root_dir: str,
    section: str,
    asset_type: str,
    asset_id: str
) -> Dict[str, Any]:
    """
    构建单条素材记录。
    第一版 tags 先留空，后面你可以手工补，也可以以后做菜单补。
    """
    rel_path = to_relative_path(abs_path, root_dir)

    return {
        "asset_id": asset_id,
        "file": rel_path,
        "type": asset_type,
        "section": section,
        "tags": [],
        "enabled": True
    }


# =========================
# 主扫描逻辑
# =========================

def scan_asset_folder(base_dir: str) -> List[Dict[str, Any]]:
    """
    扫描整个 assets 目录，收集素材记录。
    """
    root_dir = get_project_root()

    if not os.path.exists(base_dir):
        raise FileNotFoundError(f"找不到素材目录: {base_dir}")

    collected: List[Dict[str, Any]] = []
    counters: Dict[str, int] = {
        "intro_image": 0,
        "intro_video": 0,
        "hook_image": 0,
        "hook_video": 0,
        "explain_image": 0,
        "explain_video": 0,
        "unknown_image": 0,
        "unknown_video": 0,
        "unknown_unknown": 0,
    }

    for current_root, _, files in os.walk(base_dir):
        for filename in files:
            abs_path = os.path.join(current_root, filename)

            if not is_supported_asset(abs_path):
                continue

            asset_type = infer_type_from_ext(abs_path)
            section = infer_section_from_path(abs_path)

            counter_key = f"{section}_{asset_type}"
            if counter_key not in counters:
                counters[counter_key] = 0

            counters[counter_key] += 1
            asset_id = build_asset_id(section, asset_type, counters[counter_key])

            record = build_asset_record(
                abs_path=abs_path,
                root_dir=root_dir,
                section=section,
                asset_type=asset_type,
                asset_id=asset_id
            )
            collected.append(record)

    return collected


def ensure_parent_dir(file_path: str) -> None:
    """
    确保输出文件的父目录存在。
    """
    parent = os.path.dirname(file_path)
    os.makedirs(parent, exist_ok=True)


def save_asset_index(assets: List[Dict[str, Any]], output_json: str) -> None:
    """
    保存 asset_index.json
    """
    ensure_parent_dir(output_json)

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(assets, f, ensure_ascii=False, indent=2)


def build_asset_index(base_dir: str | None = None, output_json: str | None = None) -> List[Dict[str, Any]]:
    """
    主函数：
    扫描 assets，生成 asset_index.json，并返回素材列表。
    """
    assets_dir = base_dir or get_assets_dir()
    output_path = output_json or get_output_json_path()

    assets = scan_asset_folder(assets_dir)
    save_asset_index(assets, output_path)

    return assets


# =========================
# 测试输出
# =========================

def print_summary(assets: List[Dict[str, Any]]) -> None:
    """
    打印扫描汇总信息。
    """
    total = len(assets)
    intro_count = sum(1 for a in assets if a.get("section") == "intro")
    hook_count = sum(1 for a in assets if a.get("section") == "hook")
    explain_count = sum(1 for a in assets if a.get("section") == "explain")
    image_count = sum(1 for a in assets if a.get("type") == "image")
    video_count = sum(1 for a in assets if a.get("type") == "video")

    print("\n" + "=" * 50)
    print("素材扫描完成")
    print("=" * 50)
    print(f"总素材数   : {total}")
    print(f"intro 数量 : {intro_count}")
    print(f"hook 数量  : {hook_count}")
    print(f"explain 数量: {explain_count}")
    print(f"图片数量   : {image_count}")
    print(f"视频数量   : {video_count}")


def print_preview(assets: List[Dict[str, Any]], limit: int = 10) -> None:
    """
    打印前几条预览。
    """
    print("\n" + "=" * 50)
    print(f"前 {min(limit, len(assets))} 条素材预览")
    print("=" * 50)

    for i, asset in enumerate(assets[:limit], start=1):
        print(
            f"{i}. asset_id={asset.get('asset_id', '')} | "
            f"section={asset.get('section', '')} | "
            f"type={asset.get('type', '')} | "
            f"file={asset.get('file', '')}"
        )


def run_demo_test() -> None:
    """
    单文件演示测试。
    """
    assets_dir = get_assets_dir()
    output_json = get_output_json_path()

    print(f"项目根目录: {get_project_root()}")
    print(f"素材目录: {assets_dir}")
    print(f"输出文件: {output_json}")

    try:
        assets = build_asset_index(assets_dir, output_json)
    except Exception as e:
        print(f"\n生成 asset_index.json 失败: {e}")
        print("请先确认 assets/ 目录存在，并在其中放入图片或视频素材。")
        return

    print_summary(assets)
    print_preview(assets, limit=10)

    print("\nasset_index.json 已生成。")


if __name__ == "__main__":
    run_demo_test()