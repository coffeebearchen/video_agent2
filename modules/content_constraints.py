# ContentSpec-Constraint-A：最小内容约束层

import re
from typing import Dict


CHINESE_PUNCTUATION = "，。！？；：、“”‘’（）《》【】—…·,.!?;:'\"()[]{}<>/\\|@#$%^&*_+=~`"
PUNCT_PATTERN = f"[{re.escape(CHINESE_PUNCTUATION)}]"

TITLE_MAX_CHARS = 16
TITLE_SOFT_MIN_CHARS = 6
TITLE_NATURAL_MIN_CHARS = 10

# 用于寻找更自然标题边界的弱规则词
TITLE_BOUNDARY_TOKENS = [
    "影响", "决定", "改变", "推动", "压制", "重塑",
    "如何", "为什么", "什么", "是否",
    "的", "是", "让", "把", "对", "与", "和", "及", "在", "中", "下",
]
TITLE_BAD_TAILS = ["的", "是", "在", "和", "与", "及", "对", "把", "让", "中", "下"]


def remove_punctuation(text: str) -> str:
    if not text:
        return ""
    text = re.sub(PUNCT_PATTERN, "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_spaces(text: str) -> str:
    if not text:
        return ""
    return re.sub(r"\s+", " ", text).strip()


def clamp_chinese_phrase(text: str, max_chars: int) -> str:
    """
    直接按字符截断中文短语。
    当前阶段不做复杂语义分析，只做强约束。
    """
    text = remove_punctuation(text)
    text = text.replace(" ", "")
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def _pick_better_title_cut(text: str, max_chars: int = TITLE_MAX_CHARS) -> str:
    """
    尝试找到比“硬截断”更自然的标题切分点。
    规则非常保守：
    1. 先在 max_chars 范围内寻找边界词
    2. 优先取较靠后的自然边界
    3. 太短则放弃，回退硬截断
    """
    if len(text) <= max_chars:
        return text

    search_text = text[:max_chars + 1]
    best_cut = -1

    for token in TITLE_BOUNDARY_TOKENS:
        start = 0
        while True:
            idx = search_text.find(token, start)
            if idx == -1:
                break

            candidate_cut = idx + len(token)

            if TITLE_SOFT_MIN_CHARS <= candidate_cut <= max_chars:
                if candidate_cut > best_cut:
                    best_cut = candidate_cut

            start = idx + 1

    if best_cut != -1:
        return search_text[:best_cut]

    return text[:max_chars]


def _cleanup_title_tail(text: str, min_chars: int = TITLE_SOFT_MIN_CHARS) -> str:
    """
    清理不适合作为标题结尾的虚词，避免标题收尾发虚。
    """
    while len(text) > min_chars and any(text.endswith(tail) for tail in TITLE_BAD_TAILS):
        text = text[:-1]
    return text


def clamp_title_text(text: str, max_chars: int = TITLE_MAX_CHARS) -> str:
    """
    Title 规则：
    - 去标点
    - 去空格
    - 优先自然边界截断
    - 最终不超过16字
    """
    text = remove_punctuation(text)
    text = text.replace(" ", "")

    if not text:
        return ""

    hard_candidate = _cleanup_title_tail(text[:max_chars], min_chars=TITLE_SOFT_MIN_CHARS)

    if len(text) <= max_chars:
        return hard_candidate

    candidate = _pick_better_title_cut(text, max_chars=max_chars)
    candidate = _cleanup_title_tail(candidate, min_chars=TITLE_SOFT_MIN_CHARS)

    if candidate and len(candidate) >= TITLE_NATURAL_MIN_CHARS:
        return candidate[:max_chars]

    if hard_candidate:
        return hard_candidate[:max_chars]

    return text[:max_chars]


def clamp_english_phrase_by_words(text: str, max_chars: int = 16) -> str:
    """
    英文规则：
    - 去标点
    - 按单词截断
    - 不拆词
    - 尽量保持短语形态
    """
    text = remove_punctuation(text)
    text = normalize_spaces(text)
    if not text:
        return ""

    words = text.split(" ")
    result_words = []
    current_length = 0

    for word in words:
        if not word:
            continue

        added_length = len(word) if not result_words else len(word) + 1
        if current_length + added_length <= max_chars:
            result_words.append(word)
            current_length += added_length
        else:
            break

    if result_words:
        return " ".join(result_words)

    return words[0]


def constrain_title_text(text: str) -> str:
    """
    Title 最终规范化。
    """
    return clamp_title_text(text, max_chars=TITLE_MAX_CHARS)


def constrain_highlight_zh(text: str) -> str:
    """
    Highlight 中文最终规范化：
    - 去标点
    - 最多8字
    """
    return clamp_chinese_phrase(text, max_chars=8)


def constrain_highlight_en(text: str) -> str:
    """
    Highlight 英文最终规范化：
    - 去标点
    - 按词截断
    - 不拆词
    """
    return clamp_english_phrase_by_words(text, max_chars=16)


def apply_content_constraints(
    title_text: str,
    highlight_zh: str,
    highlight_en: str,
) -> Dict[str, str]:
    """
    统一输出约束后的 title / highlight。
    """
    constrained_title = constrain_title_text(title_text)
    constrained_highlight_zh = constrain_highlight_zh(highlight_zh)
    constrained_highlight_en = constrain_highlight_en(highlight_en)

    return {
        "title": constrained_title,
        "highlight_zh": constrained_highlight_zh,
        "highlight_en": constrained_highlight_en,
    }