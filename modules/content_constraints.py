# ContentSpec-Constraint-A：最小内容约束层

import re
from typing import Dict


CHINESE_PUNCTUATION = "，。！？；：、“”‘’（）《》【】—…·,.!?;:'\"()[]{}<>/\\|@#$%^&*_+=~`"
PUNCT_PATTERN = f"[{re.escape(CHINESE_PUNCTUATION)}]"


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


def clamp_title_text(text: str, max_chars: int = 16) -> str:
    """
    Title 规则：
    - 去标点
    - 最多16字
    - 当前先只做纯文本长度约束
    """
    text = remove_punctuation(text)
    text = text.replace(" ", "")
    if len(text) <= max_chars:
        return text
    return text[:max_chars]


def clamp_english_phrase_by_words(text: str, max_chars: int = 20) -> str:
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
    return clamp_title_text(text, max_chars=16)


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
    return clamp_english_phrase_by_words(text, max_chars=20)


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