from __future__ import annotations

import re
from typing import Dict


STYLE_CONTENT_DIRECTIONS = {
    "creator_clean": {
        "title_tone": "简洁中性",
        "highlight_tone": "关键词",
    },
    "product_focus": {
        "title_tone": "产品价值",
        "highlight_tone": "功能结果",
    },
    "life_story": {
        "title_tone": "人话叙事",
        "highlight_tone": "情绪变化",
    },
    "ai_control_lab": {
        "title_tone": "结构分析",
        "highlight_tone": "系统约束",
    },
    "personal_ip": {
        "title_tone": "鲜明观点",
        "highlight_tone": "判断短句",
    },
}

RESULT_WORDS = ("更快", "更稳", "更准", "更省", "效率", "精度", "稳定", "控制", "系统", "变量", "约束", "信号")
EMOTION_WORDS = ("焦虑", "后来", "终于", "改变", "一下子", "慢慢", "原来")


def _clean_text(text: str) -> str:
    return " ".join(str(text or "").replace("\n", " ").split()).strip()


def _truncate(text: str, limit: int) -> str:
    cleaned = _clean_text(text)
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[:limit].rstrip("，,。；;：: ")


def _first_segment(text: str) -> str:
    cleaned = _clean_text(text)
    if not cleaned:
        return ""
    for splitter in ("，", ",", "。", "；", ";", "：", ":"):
        if splitter in cleaned:
            return cleaned.split(splitter, 1)[0].strip()
    return cleaned


def _last_segment(text: str) -> str:
    cleaned = _clean_text(text)
    if not cleaned:
        return ""
    for splitter in ("，", ",", "。", "；", ";", "：", ":"):
        if splitter in cleaned:
            return cleaned.rsplit(splitter, 1)[-1].strip()
    return cleaned


def _compress_keyword(text: str, limit: int = 12) -> str:
    cleaned = _clean_text(text)
    if not cleaned:
        return ""
    candidate = _first_segment(cleaned)
    candidate = re.sub(r"^(而是|真正的问题是|真正的问题，不是|真正的问题|关键不是|你必须知道)[:：，,\s]*", "", candidate)
    candidate = candidate.strip()
    if len(candidate) > limit:
        candidate = candidate[:limit]
    return candidate.strip("，,。；;：: ")


def _extract_negative_target(text: str) -> str:
    cleaned = _clean_text(text)
    match = re.search(r"不是(.+)$", cleaned)
    if match:
        return match.group(1).strip("，,。；;：: ")
    return ""


def _extract_method_target(text: str) -> str:
    cleaned = _clean_text(text)
    cleaned = re.sub(r"^(而是|其实是|关键是|真正的问题是)[:：，,\s]*", "", cleaned)
    if "错误的方法" in cleaned:
        return "方法错了"
    if "方法" in cleaned:
        return _truncate(_first_segment(cleaned), 8)
    return _compress_keyword(cleaned, limit=10)


def _find_result_word(text: str) -> str:
    cleaned = _clean_text(text)
    for word in RESULT_WORDS:
        if word in cleaned:
            return word
    return ""


def _find_emotion_word(text: str) -> str:
    cleaned = _clean_text(text)
    for word in EMOTION_WORDS:
        if word in cleaned:
            return word
    return ""


def _apply_creator_clean(title: str, highlight: str) -> Dict[str, str]:
    title_result = _extract_negative_target(title)
    if title_result:
        title_result = f"问题不在{_truncate(title_result, 6)}"
    else:
        title_result = _compress_keyword(title, limit=12) or _truncate(title, 12)

    highlight_core = _extract_method_target(highlight)
    highlight_result = highlight_core or _compress_keyword(highlight, limit=10) or _truncate(highlight, 10)
    return {"title": title_result, "highlight": highlight_result}


def _apply_product_focus(title: str, highlight: str) -> Dict[str, str]:
    result_word = _find_result_word(highlight) or _find_result_word(title)
    negative_target = _extract_negative_target(title)
    title_core = negative_target or _compress_keyword(title, limit=14) or _truncate(title, 14)
    highlight_core = _extract_method_target(highlight) or _compress_keyword(highlight, limit=10) or _truncate(highlight, 10)
    title_result = f"效率问题，不在{_truncate(title_core, 8)}" if title_core else title
    if result_word:
        highlight_result = f"{result_word}更直接"
    else:
        highlight_result = f"结果更明确：{highlight_core}" if highlight_core else highlight
    return {"title": _truncate(title_result, 18), "highlight": _truncate(highlight_result, 12)}


def _apply_life_story(title: str, highlight: str) -> Dict[str, str]:
    title_core = _clean_text(title)
    highlight_core = _clean_text(highlight)
    emotion_word = _find_emotion_word(highlight_core) or _find_emotion_word(title_core)
    title_result = f"后来才发现，{title_core}" if title_core and not title_core.startswith("后来") else title_core
    if emotion_word:
        highlight_result = f"{emotion_word}之后，才开始改变"
    else:
        highlight_result = f"后来才意识到：{_first_segment(highlight_core)}" if highlight_core else highlight
    return {"title": _truncate(title_result, 22), "highlight": _truncate(highlight_result, 16)}


def _apply_ai_control_lab(title: str, highlight: str) -> Dict[str, str]:
    title_core = _extract_negative_target(title) or _compress_keyword(title, limit=12) or _truncate(title, 12)
    highlight_core = _extract_method_target(highlight) or _compress_keyword(highlight, limit=12) or _truncate(highlight, 12)
    title_result = f"问题诊断：{title_core}" if title_core else title
    if highlight_core:
        highlight_result = f"核心约束：{highlight_core}"
    else:
        highlight_result = highlight
    return {"title": _truncate(title_result, 18), "highlight": _truncate(highlight_result, 18)}


def _apply_personal_ip(title: str, highlight: str) -> Dict[str, str]:
    title_core = _extract_negative_target(title) or _compress_keyword(title, limit=14) or _truncate(title, 14)
    highlight_core = _extract_method_target(highlight) or _compress_keyword(highlight, limit=14) or _truncate(highlight, 14)
    title_result = f"真正的问题是：{title_core}" if title_core else title
    highlight_result = f"你必须知道：{highlight_core}" if highlight_core else highlight
    return {"title": _truncate(title_result, 22), "highlight": _truncate(highlight_result, 20)}


def apply_style_content_link(style_name: str, title: str, highlight: str) -> Dict[str, str]:
    cleaned_title = _clean_text(title)
    cleaned_highlight = _clean_text(highlight)

    if not cleaned_title and not cleaned_highlight:
        return {"title": cleaned_title, "highlight": cleaned_highlight}

    try:
        if style_name == "creator_clean":
            return _apply_creator_clean(cleaned_title, cleaned_highlight)
        if style_name == "product_focus":
            return _apply_product_focus(cleaned_title, cleaned_highlight)
        if style_name == "life_story":
            return _apply_life_story(cleaned_title, cleaned_highlight)
        if style_name == "ai_control_lab":
            return _apply_ai_control_lab(cleaned_title, cleaned_highlight)
        if style_name == "personal_ip":
            return _apply_personal_ip(cleaned_title, cleaned_highlight)
    except Exception:
        return {"title": cleaned_title, "highlight": cleaned_highlight}

    return {"title": cleaned_title, "highlight": cleaned_highlight}