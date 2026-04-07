# -*- coding: utf-8 -*-
"""
app.py

最小 Web Demo：
1. 提供单页输入界面
2. 接收原文并生成多风格视频文案结果
3. 只做网页包装层，不改底层主链模块
"""

import json

from flask import Flask, jsonify, render_template, request
from frontend.routes.content_processor import register_content_processor_routes

from modules.output_adapter import adapt_ai_output
from modules.preview_enhancer import build_enhanced_preview
from modules.prompt_builder import build_prompt
from modules.llm_client import call_llm
from modules.style_prompt_enhancer import enhance_style_prompt


app = Flask(__name__)
register_content_processor_routes(app)

DEFAULT_STYLES = ["knowledge", "authority", "story"]
ALLOWED_CONTENT_MODES = {"finance", "product", "ads"}


def _compact_text(text: str) -> str:
    return "".join(ch for ch in str(text or "") if ch not in " \t\r\n，。！？；：,.!?;:\"'“”‘’（）()[]【】")


def _strip_code_fence(text: str) -> str:
    normalized = str(text or "").strip()
    if not normalized.startswith("```"):
        return normalized

    lines = normalized.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _extract_json_text(text: str) -> str:
    normalized = _strip_code_fence(text)
    start = normalized.find("{")
    end = normalized.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return ""
    return normalized[start:end + 1]


def _parse_demo_payload(raw_output: str) -> dict:
    normalized = str(raw_output or "").strip()
    if not normalized:
        return {}

    try:
        parsed = json.loads(normalized)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass

    json_text = _extract_json_text(normalized)
    if not json_text:
        return {}

    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        return {}

    return parsed if isinstance(parsed, dict) else {}


def _normalize_demo_output_payload(payload: dict) -> dict:
    normalized = payload if isinstance(payload, dict) else {}
    title = normalized.get("title")
    highlight = normalized.get("highlight")
    if not highlight and normalized.get("highlights"):
        highlight = normalized.get("highlights")

    return {
        "title": title,
        "highlight": highlight,
    }


def _split_raw_parts(raw_text: str) -> list[str]:
    text = str(raw_text or "").replace("\r", "\n")
    separators = ["。", "！", "？", "；", "\n", "，", ","]
    parts = [text]
    for separator in separators:
        next_parts: list[str] = []
        for part in parts:
            next_parts.extend(part.split(separator))
        parts = next_parts
    return [part.strip() for part in parts if part.strip()]


def _build_style_safe_output(raw_text: str, style_mode: str) -> dict:
    parts = _split_raw_parts(raw_text)
    first = parts[0] if parts else "内容重点"
    second = parts[1] if len(parts) > 1 else first
    third = parts[2] if len(parts) > 2 else second

    style_key = str(style_mode or "").strip().lower()
    if style_key == "authority":
        title = f"{first[:10]}，关键看{second[:10]}"
        highlight = [first[:18], second[:18]]
    elif style_key == "story":
        title = f"别只看{first[:8]}，真正关键是{second[:10]}"
        highlight = [first[:18], second[:18], third[:18]]
    else:
        title = f"{first[:10]}，关键看{second[:10]}"
        highlight = [first[:18], second[:18], third[:18]]

    cleaned_highlight = [item.rstrip("，,。；;：:、 ") for item in highlight if item.rstrip("，,。；;：:、 ")]
    return {
        "title": title.rstrip("，,。；;：:、 ") or "内容重点",
        "highlight": cleaned_highlight or ["内容重点"],
    }


def _is_grounded_output(adapted_output: dict, raw_text: str) -> bool:
    source = _compact_text(raw_text)
    if len(source) < 4:
        return True

    combined_output = _compact_text(adapted_output.get("title", ""))
    for item in adapted_output.get("highlight", []):
        combined_output += _compact_text(item)

    if not combined_output:
        return False

    for index in range(len(source) - 3):
        fragment = source[index:index + 4]
        if fragment and fragment in combined_output:
            return True
    return False


def _generate_style_result(raw_text: str, content_mode: str, style_mode: str) -> dict:
    base_prompt_result = build_prompt(
        raw_text=raw_text,
        content_mode=content_mode,
        style_mode=style_mode,
        user_intent=None,
    )
    enhanced_prompt = enhance_style_prompt(style_mode, base_prompt_result["prompt"])

    try:
        raw_output = call_llm(enhanced_prompt)
        parsed_output = _normalize_demo_output_payload(_parse_demo_payload(raw_output))
    except Exception:
        parsed_output = {}

    adapted_output = adapt_ai_output(parsed_output)
    if not adapted_output["title"] or not adapted_output["highlight"]:
        adapted_output = adapt_ai_output(_build_style_safe_output(raw_text, style_mode))
    elif not _is_grounded_output(adapted_output, raw_text):
        adapted_output = adapt_ai_output(_build_style_safe_output(raw_text, style_mode))

    preview = build_enhanced_preview(
        title=adapted_output["title"],
        highlight=adapted_output["highlight"],
    )

    return {
        "style_mode": style_mode,
        "title": preview["headline"],
        "scenes": [scene.get("text", "") for scene in preview.get("scenes", []) if scene.get("text", "")],
    }


@app.get("/")
def index():
    """Legacy demo entry kept for rollback/reference."""
    return render_template("index.html")


@app.post("/generate")
def generate():
    payload = request.get_json(silent=True) or {}
    raw_text = str(payload.get("text", "") or "").strip()
    content_mode = str(payload.get("content_mode", "finance") or "finance").strip().lower()

    if len(raw_text) < 4:
        return jsonify({"ok": False, "message": "请输入更完整的内容。"}), 400

    if content_mode not in ALLOWED_CONTENT_MODES:
        content_mode = "finance"

    try:
        results = [
            _generate_style_result(raw_text, content_mode, style_mode)
            for style_mode in DEFAULT_STYLES
        ]
        return jsonify({"ok": True, "results": results})
    except Exception:
        return jsonify({"ok": False, "message": "生成失败，请稍后重试"}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)