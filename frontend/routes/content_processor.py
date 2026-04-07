# -*- coding: utf-8 -*-
"""
正式 Content Processor 页面入口。

说明：
1. 只负责提供正式内容处理骨架页访问路径
2. 提供正式 Generate API，但不接表达模块、不接数据库
3. 与旧 demo 入口分离，便于后续正式流独立演进
"""

import json

from flask import jsonify, render_template, request

from modules.content_processor.content_package_builder import build_content_package
from modules.content_processor.reference_media_store import build_reference_media


ALLOWED_CONTENT_MODES = {"finance", "product", "ads"}
ALLOWED_STYLE_MODES = {"knowledge", "authority", "story", "product", "ads"}


def _parse_assets_meta(raw_value: str | None) -> dict:
    text = str(raw_value or "").strip()
    if not text:
        return {}

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}

    return parsed if isinstance(parsed, dict) else {}


def _normalize_generate_payload(payload: dict) -> dict:
    raw_text = str(payload.get("raw_text", "") or "").strip()
    content_mode = str(payload.get("content_mode", "finance") or "finance").strip().lower()
    style_mode = str(payload.get("style_mode", "knowledge") or "knowledge").strip().lower()
    feedback_text = str(payload.get("feedback_text", "") or "").strip()
    auto_flow = bool(payload.get("auto_flow", False))

    if content_mode not in ALLOWED_CONTENT_MODES:
        content_mode = "finance"
    if style_mode not in ALLOWED_STYLE_MODES:
        style_mode = "knowledge"

    try:
        script_length_target = int(payload.get("script_length_target", 100) or 100)
    except Exception:
        script_length_target = 100

    return {
        "raw_text": raw_text,
        "content_mode": content_mode,
        "style_mode": style_mode,
        "script_length_target": script_length_target,
        "feedback_text": feedback_text,
        "auto_flow": auto_flow,
    }


def _read_generate_request() -> dict:
    if request.content_type and "multipart/form-data" in request.content_type.lower():
        payload = _normalize_generate_payload(request.form.to_dict())
        image_assets_meta = _parse_assets_meta(request.form.get("image_assets_meta"))
        video_assets_meta = _parse_assets_meta(request.form.get("video_assets_meta"))
        payload["reference_media"] = build_reference_media(
            image_files=request.files.getlist("reference_images[]"),
            image_note=request.form.get("reference_images_note", ""),
            image_role_hint=request.form.get("reference_images_role_hint", "hook"),
            image_assets_meta=image_assets_meta,
            video_files=request.files.getlist("reference_videos[]"),
            video_note=request.form.get("reference_videos_note", ""),
            video_role_hint=request.form.get("reference_videos_role_hint", "primary"),
            video_assets_meta=video_assets_meta,
        )
        return payload

    payload = _normalize_generate_payload(request.get_json(silent=True) or {})
    payload["reference_media"] = {
        "image_group": None,
        "video_group": None,
    }
    return payload


def register_content_processor_routes(app) -> None:
    @app.get("/content-processor")
    def content_processor_dashboard():
        return render_template("content_processor/dashboard.html")

    @app.post("/content-processor/generate")
    def content_processor_generate():
        try:
            payload = _read_generate_request()
        except ValueError as error:
            return jsonify({"ok": False, "message": str(error)}), 400

        if len(payload["raw_text"]) < 4:
            return jsonify({"ok": False, "message": "请输入更完整的内容。"}), 400

        try:
            content_package = build_content_package(**payload)
            return jsonify(content_package)
        except Exception:
            return jsonify({"ok": False, "message": "内容生成失败，请稍后重试。"}), 500