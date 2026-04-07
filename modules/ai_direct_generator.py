# -*- coding: utf-8 -*-
"""
文件名：ai_direct_generator.py
作用说明：
1. 作为 AI 直出最小生成模块
2. 串接 prompt_builder 与 llm_client
3. 解析模型结果，并提供极薄 fallback
"""

import json
import re
from typing import Any

from modules.llm_client import call_llm, get_llm_runtime_meta
from modules.prompt_builder import build_prompt


TITLE_PREFIX_PATTERN = re.compile(r"^(title|标题)\s*[:：-]\s*", re.IGNORECASE)
LIST_PREFIX_PATTERN = re.compile(r"^\s*(?:[-*•]+|\d+[.)、])\s*")
QUOTE_CHARS = "\"'“”‘’「」『』"
FALLBACK_HIGHLIGHT_COUNT = {
    "authority": 1,
    "knowledge": 2,
    "product": 2,
    "ads": 2,
    "story": 2,
}


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


def _parse_llm_payload(raw_output: str) -> dict[str, Any] | None:
    normalized = str(raw_output or "").strip()
    if not normalized:
        return None

    try:
        parsed = json.loads(normalized)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        pass

    json_text = _extract_json_text(normalized)
    if not json_text:
        return None

    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        return None

    return parsed if isinstance(parsed, dict) else None


def _clean_title(text: Any) -> str:
    value = str(text or "").strip()
    value = value.strip(QUOTE_CHARS).strip()
    value = TITLE_PREFIX_PATTERN.sub("", value)
    value = value.strip(QUOTE_CHARS).strip()
    if len(value) > 24:
        value = value[:24].rstrip("，,。；;：:、 ")
    return value


def _clean_highlight_item(text: Any) -> str:
    value = str(text or "").strip()
    value = value.strip(QUOTE_CHARS).strip()
    value = LIST_PREFIX_PATTERN.sub("", value)
    value = value.strip(QUOTE_CHARS).strip()
    if len(value) > 24:
        value = value[:24].rstrip("，,。；;：:、 ")
    return value


def _normalize_highlight(value: Any) -> list[str]:
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        items = [value]
    elif value is None:
        items = []
    else:
        items = [str(value)]

    results: list[str] = []
    for item in items:
        cleaned = _clean_highlight_item(item)
        if cleaned:
            results.append(cleaned)
    return results


def _split_text_segments(raw_text: str) -> list[str]:
    normalized = str(raw_text or "").replace("\r", "\n")
    primary_parts = re.split(r"[。！？；\n]+", normalized)
    results: list[str] = []

    for part in primary_parts:
        part = part.strip()
        if not part:
            continue
        sub_parts = re.split(r"[，,]+", part)
        for item in sub_parts:
            cleaned = _clean_highlight_item(item)
            if cleaned:
                results.append(cleaned)

    deduped: list[str] = []
    seen: set[str] = set()
    for item in results:
        if item not in seen:
            seen.add(item)
            deduped.append(item)
    return deduped


def _fallback_title(raw_text: str) -> str:
    segments = _split_text_segments(raw_text)
    if not segments:
        return "内容重点"

    title = segments[0]
    if len(title) > 16:
        title = title[:16].rstrip("，,。；;：:、 ")
    return title or "内容重点"


def _fallback_highlight(raw_text: str, style_mode: str) -> list[str]:
    segments = _split_text_segments(raw_text)
    if not segments:
        return ["信息要点"]

    desired_count = FALLBACK_HIGHLIGHT_COUNT.get(str(style_mode or "").strip().lower(), 2)
    return segments[:desired_count] or ["信息要点"]


def generate_ai_direct(
    raw_text: str,
    content_mode: str,
    style_mode: str,
    user_intent: dict | None = None,
) -> dict:
    """生成标准结构的 AI 直出结果。"""
    prompt_result = build_prompt(
        raw_text=raw_text,
        content_mode=content_mode,
        style_mode=style_mode,
        user_intent=user_intent,
    )
    runtime_meta = get_llm_runtime_meta()

    fallback_used = False
    raw_output = ""
    try:
        raw_output = call_llm(prompt_result["prompt"])
    except Exception:
        fallback_used = True

    parsed = _parse_llm_payload(raw_output)
    if parsed is None:
        fallback_used = True
        parsed = {}

    title = _clean_title(parsed.get("title"))
    highlight = _normalize_highlight(parsed.get("highlight"))

    if not highlight:
        highlight = _normalize_highlight(parsed.get("highlights"))

    if not title:
        fallback_used = True
        title = _fallback_title(raw_text)

    if not highlight:
        fallback_used = True
        highlight = _fallback_highlight(raw_text, style_mode)

    return {
        "title": title,
        "highlight": highlight,
        "meta": {
            "content_mode": prompt_result["meta"]["content_mode"],
            "style_mode": prompt_result["meta"]["style_mode"],
            "auto_mode": prompt_result["meta"]["auto_mode"],
            "user_intent_used": prompt_result["meta"]["user_intent_used"],
            "model_used": runtime_meta["model"],
            "fallback_used": fallback_used,
        },
    }