# -*- coding: utf-8 -*-
"""
script_enhancer.py

表达节奏增强层：
- 不改变原意
- 不新增信息
- 只做轻量说话节奏优化
"""

import re


def _normalize_text(text: str) -> str:
    cleaned = str(text or "").strip()
    cleaned = re.sub(r"\r\n?", "\n", cleaned)
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n+", "\n", cleaned)
    return cleaned


def _split_sentences(text: str):
    return [part for part in re.findall(r"[^。！？!?]+[。！？!?]?", text) if part.strip()]


def _enhance_sentence_rhythm(sentence: str) -> str:
    enhanced = sentence.strip()
    if not enhanced:
        return enhanced

    if enhanced[-1] not in "。！？!?":
        enhanced = f"{enhanced}。"

    enhanced = re.sub(r"(?<=[^，,。！？!?\n]{6})(但|却|不过|而是|所以|因此|于是|同时)", r"，\n\1", enhanced, count=1)
    enhanced = re.sub(r"，(但|却|不过|而是|所以|因此|于是|同时)", r"，\n\1", enhanced)

    if "\n" not in enhanced:
        enhanced = re.sub(r"(?<=[^，,。！？!?\n]{10})，(?=[^，,。！？!?\n]{8,})", "，\n", enhanced, count=1)

    return enhanced


def enhance_speech_rhythm(text: str) -> str:
    normalized = _normalize_text(text)
    if not normalized:
        return normalized

    sentences = _split_sentences(normalized)
    if not sentences:
        return normalized

    enhanced_sentences = [_enhance_sentence_rhythm(sentence) for sentence in sentences]
    return "\n".join(part for part in enhanced_sentences if part)
