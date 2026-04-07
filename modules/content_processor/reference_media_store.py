# -*- coding: utf-8 -*-
"""
参考素材输入层：保存上传文件并生成组级输入结构。

职责：
1. 接收图片组 / 视频组上传文件
2. 以规范目录保存文件
3. 返回统一 reference_media 结构，供 builder 与 content package 使用
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
UPLOAD_ROOT = PROJECT_ROOT / "data" / "users" / "default_user" / "uploads"
IMAGE_UPLOAD_DIR = UPLOAD_ROOT / "images"
VIDEO_UPLOAD_DIR = UPLOAD_ROOT / "videos"

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}
ALLOWED_ROLE_HINTS = {"primary", "hook", "supporting"}


def _normalize_role_hint(role_hint: str | None, default_value: str) -> str:
    normalized = str(role_hint or "").strip().lower()
    if normalized in ALLOWED_ROLE_HINTS:
        return normalized
    return default_value


def _normalize_note(note: str | None) -> str:
    return str(note or "").strip()


def _normalize_assets_meta(assets_meta: dict | None) -> list[dict]:
    if not isinstance(assets_meta, dict):
        return []

    assets = assets_meta.get("assets")
    if not isinstance(assets, list):
        return []

    normalized_assets = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        normalized_assets.append(
            {
                "asset_id": str(asset.get("asset_id") or "").strip(),
                "file_name": str(asset.get("file_name") or "").strip(),
                "asset_type": str(asset.get("asset_type") or "").strip(),
                "upload_status": str(asset.get("upload_status") or "").strip() or "pending",
            }
        )

    return normalized_assets


def _ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _store_file(file_storage, target_dir: Path, allowed_extensions: set[str], media_type: str, asset_meta: dict | None = None) -> dict | None:
    filename = str(getattr(file_storage, "filename", "") or "").strip()
    if not filename:
        return None

    suffix = Path(filename).suffix.lower()
    if suffix not in allowed_extensions:
        raise ValueError(f"unsupported {media_type} file type: {suffix}")

    _ensure_directory(target_dir)
    stored_name = f"{uuid4().hex}{suffix}"
    target_path = target_dir / stored_name
    file_storage.save(target_path)

    normalized_meta = asset_meta if isinstance(asset_meta, dict) else {}

    return {
        "media_type": media_type,
        "original_name": filename,
        "file_name": normalized_meta.get("file_name") or filename,
        "asset_id": normalized_meta.get("asset_id") or "",
        "asset_type": normalized_meta.get("asset_type") or media_type,
        "upload_status": normalized_meta.get("upload_status") or "ready",
        "stored_name": stored_name,
        "path": str(target_path.relative_to(PROJECT_ROOT)).replace("\\", "/"),
    }


def _build_group(files, note: str, role_hint: str, media_type: str, assets_meta: dict | None = None) -> dict | None:
    if media_type == "image":
        target_dir = IMAGE_UPLOAD_DIR
        allowed_extensions = ALLOWED_IMAGE_EXTENSIONS
        default_role = "hook"
    else:
        target_dir = VIDEO_UPLOAD_DIR
        allowed_extensions = ALLOWED_VIDEO_EXTENSIONS
        default_role = "primary"

    assets = []
    normalized_assets_meta = _normalize_assets_meta(assets_meta)
    for index, file_storage in enumerate(files):
        asset_meta = normalized_assets_meta[index] if index < len(normalized_assets_meta) else None
        stored_asset = _store_file(file_storage, target_dir, allowed_extensions, media_type, asset_meta)
        if stored_asset:
            assets.append(stored_asset)

    normalized_note = _normalize_note(note)
    normalized_role = _normalize_role_hint(role_hint, default_role)
    if not assets and not normalized_note:
        return None

    return {
        "role_hint": normalized_role,
        "note": normalized_note,
        "assets": assets,
    }


def build_reference_media(
    image_files,
    image_note: str | None,
    image_role_hint: str | None,
    image_assets_meta: dict | None,
    video_files,
    video_note: str | None,
    video_role_hint: str | None,
    video_assets_meta: dict | None,
) -> dict:
    image_group = _build_group(image_files, image_note, image_role_hint, "image", image_assets_meta)
    video_group = _build_group(video_files, video_note, video_role_hint, "video", video_assets_meta)

    return {
        "image_group": image_group,
        "video_group": video_group,
    }