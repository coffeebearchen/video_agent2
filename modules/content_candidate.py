import re
from typing import Dict, List

from modules.content_constraints import constrain_highlight_zh, constrain_title_text


SENTENCE_SPLIT_PATTERN = r"[，,。！？；;：:\n]+"
TITLE_STOPWORDS = {
    "的", "了", "和", "与", "及", "在", "中", "下", "上", "对", "把", "让",
    "将", "被", "并", "也", "就", "都", "而", "但", "又", "很", "太", "更",
    "一个", "一种", "一些", "这个", "那个", "这些", "那些", "我们", "你们", "他们",
}
HIGHLIGHT_VERB_TOKENS = ["是", "做", "让", "变", "决定"]
HIGHLIGHT_COMPARE_TOKENS = ["不是", "而是", "从", "到"]


def _normalize_text(raw_text: str) -> str:
    if not raw_text:
        return ""
    return re.sub(r"\s+", "", str(raw_text)).strip()


def _split_sentences(raw_text: str) -> List[str]:
    text = str(raw_text or "")
    parts = [segment.strip() for segment in re.split(SENTENCE_SPLIT_PATTERN, text)]
    return [segment for segment in parts if segment]


def _slice_half(text: str, use_back_half: bool) -> str:
    normalized = _normalize_text(text)
    if not normalized:
        return ""

    midpoint = max(1, len(normalized) // 2)
    if use_back_half:
        return normalized[midpoint:]
    return normalized[:midpoint]


def _extract_keyword_title(text: str) -> str:
    normalized = _normalize_text(text)
    if not normalized:
        return ""

    rough_tokens = [token for token in re.split(r"[的了和与及在中上下对把让将被并也就都而但又很太更]+", normalized) if token]
    filtered_tokens = []

    for token in rough_tokens:
        if token in TITLE_STOPWORDS:
            continue
        filtered_tokens.append(token)

    if not filtered_tokens:
        return normalized

    compressed = "".join(filtered_tokens[:4])
    return compressed or normalized


def _pick_longest_sentence(sentences: List[str], fallback_text: str) -> str:
    if sentences:
        return max(sentences, key=len)
    return _normalize_text(fallback_text)


def _pick_sentence_by_tokens(sentences: List[str], tokens: List[str], fallback_text: str) -> str:
    for sentence in sentences:
        if any(token in sentence for token in tokens):
            return sentence
    return fallback_text


def constraint_title(text: str) -> str:
    return constrain_title_text(text)


def constraint_highlight(text: str) -> str:
    return constrain_highlight_zh(text)


def generate_candidates(raw_text: str) -> Dict[str, List[str]]:
    normalized = _normalize_text(raw_text)
    sentences = _split_sentences(raw_text)

    title_candidate_1 = constraint_title(_slice_half(normalized, use_back_half=False))
    title_candidate_2 = constraint_title(_slice_half(normalized, use_back_half=True))
    title_candidate_3 = constraint_title(_extract_keyword_title(normalized))

    highlight_base = _pick_longest_sentence(sentences, normalized)
    highlight_candidate_1 = constraint_highlight(highlight_base)
    highlight_candidate_2 = constraint_highlight(
        _pick_sentence_by_tokens(sentences, HIGHLIGHT_VERB_TOKENS, highlight_base)
    )
    highlight_candidate_3 = constraint_highlight(
        _pick_sentence_by_tokens(sentences, HIGHLIGHT_COMPARE_TOKENS, highlight_base)
    )

    return {
        "title_candidates": [
            title_candidate_1,
            title_candidate_2,
            title_candidate_3,
        ],
        "highlight_candidates": [
            highlight_candidate_1,
            highlight_candidate_2,
            highlight_candidate_3,
        ],
    }