import re
from typing import Dict, List

from modules.content_constraints import constrain_highlight_zh, constrain_title_text


SENTENCE_SPLIT_PATTERN = r"[，,。！？；;：:\n]+"
TITLE_STOPWORDS = {
    "的", "了", "和", "与", "及", "在", "中", "下", "上", "对", "把", "让",
    "将", "被", "并", "也", "就", "都", "而", "但", "又", "很", "太", "更",
    "一个", "一种", "一些", "这个", "那个", "这些", "那些", "我们", "你们", "他们",
}
TITLE_STRUCTURE_TOKENS = ["是", "不是", "决定", "影响", "让", "会"]
TITLE_CONCLUSION_TOKENS = ["不是", "而是", "决定", "核心", "本质", "关键", "影响"]
TITLE_COMPRESS_PHRASES = [
    "资产价格", "贴现率", "收益率", "流动性", "风险资产", "资金成本", "企业利润", "市场预期",
    "利率", "资金", "价格", "降息", "股市", "资产", "盈利", "预期", "市场",
]
BAD_ENDINGS = ["随着", "因为", "如果", "但是", "所以", "会", "在", "把", "让", "而", "就"]
HIGHLIGHT_VERB_TOKENS = ["是", "做", "让", "变", "决定"]
HIGHLIGHT_COMPARE_TOKENS = ["不是", "而是", "从", "到"]


def _normalize_text(raw_text: str) -> str:
    if not raw_text:
        return ""
    return re.sub(r"\s+", "", str(raw_text)).strip()


def split_into_segments(raw_text: str) -> List[str]:
    text = str(raw_text or "")
    parts = [segment.strip() for segment in re.split(SENTENCE_SPLIT_PATTERN, text)]
    normalized_parts = [_normalize_text(segment) for segment in parts]
    return [segment for segment in normalized_parts if segment]


def is_bad_fragment(text: str) -> bool:
    normalized = _normalize_text(text)
    if not normalized:
        return True

    if any(normalized.endswith(token) for token in BAD_ENDINGS):
        return True

    structure_hits = sum(
        1 for token in (TITLE_STRUCTURE_TOKENS + TITLE_CONCLUSION_TOKENS) if token in normalized
    )
    if len(normalized) > 16 and structure_hits >= 2:
        return True

    if len(normalized) > 12 and any(token in normalized for token in ["随着", "因为", "如果", "但是", "所以"]):
        return True

    return False


def score_segment_for_title(seg: str) -> int:
    normalized = _normalize_text(seg)
    if not normalized:
        return -1

    score = 0
    length = len(normalized)

    if 6 <= length <= 12:
        score += 2
    elif 13 <= length <= 16:
        score += 1
    elif length < 4 or length > 20:
        score -= 1

    if any(token in normalized for token in TITLE_STRUCTURE_TOKENS):
        score += 2

    if not is_bad_fragment(normalized):
        score += 2

    return score


def _extract_keyword_title(text: str) -> str:
    normalized = _normalize_text(text)
    if not normalized:
        return ""

    matches = []
    for token in TITLE_COMPRESS_PHRASES + TITLE_STRUCTURE_TOKENS:
        start = 0
        while True:
            index = normalized.find(token, start)
            if index == -1:
                break
            matches.append((index, -len(token), token))
            start = index + len(token)

    matches.sort()

    filtered_tokens = []
    last_end = -1
    for index, _, token in matches:
        if index < last_end:
            continue
        filtered_tokens.append(token)
        last_end = index + len(token)
        if len(filtered_tokens) >= 4:
            break

    if not filtered_tokens:
        rough_tokens = [
            token for token in re.split(r"[的了和与及在中上下对把让将被并也就都而但又很太更]+", normalized) if token
        ]
        for token in rough_tokens:
            if token in TITLE_STOPWORDS:
                continue
            filtered_tokens.append(token)
            if len(filtered_tokens) >= 3:
                break

    if not filtered_tokens:
        return normalized

    compressed = "".join(filtered_tokens[:4])
    return compressed or normalized


def _pick_best_scored_segment(segments: List[str]) -> str:
    if not segments:
        return ""

    best_segment = segments[0]
    best_score = score_segment_for_title(best_segment)

    for segment in segments[1:]:
        score = score_segment_for_title(segment)
        if score > best_score:
            best_segment = segment
            best_score = score

    return best_segment


def _pick_first_natural_title_segment(segments: List[str]) -> str:
    for segment in segments:
        if 6 <= len(segment) <= 16 and any(token in segment for token in TITLE_STRUCTURE_TOKENS) and not is_bad_fragment(segment):
            return segment
    return _pick_best_scored_segment(segments)


def _pick_conclusion_segment(segments: List[str], fallback_segment: str) -> str:
    best_segment = ""
    best_length = None

    for segment in segments:
        if not any(token in segment for token in TITLE_CONCLUSION_TOKENS):
            continue
        if is_bad_fragment(segment):
            continue
        segment_length = len(segment)
        if best_length is None or segment_length < best_length:
            best_segment = segment
            best_length = segment_length

    if best_segment:
        return best_segment

    passed_fallback = False
    for segment in segments:
        if segment == fallback_segment and not passed_fallback:
            passed_fallback = True
            continue
        if segment and not is_bad_fragment(segment):
            return segment

    return fallback_segment


def _pick_longest_sentence(sentences: List[str], fallback_text: str) -> str:
    if sentences:
        return max(sentences, key=len)
    return _normalize_text(fallback_text)


def _pick_sentence_by_tokens(sentences: List[str], tokens: List[str], fallback_text: str) -> str:
    for sentence in sentences:
        if any(token in sentence for token in tokens):
            return sentence
    return fallback_text


def _pick_highlight_base(segments: List[str], fallback_text: str, preferred_segment: str) -> str:
    if preferred_segment and not is_bad_fragment(preferred_segment):
        return preferred_segment

    for segment in segments:
        if not is_bad_fragment(segment):
            return segment

    return _pick_longest_sentence(segments, fallback_text)


def constraint_title(text: str) -> str:
    return constrain_title_text(text)


def constraint_highlight(text: str) -> str:
    return constrain_highlight_zh(text)


def generate_candidates(raw_text: str) -> Dict[str, List[str]]:
    normalized = _normalize_text(raw_text)
    segments = split_into_segments(raw_text)

    best_natural_segment = _pick_first_natural_title_segment(segments)
    conclusion_segment = _pick_conclusion_segment(segments, best_natural_segment)

    title_candidate_1 = constraint_title(best_natural_segment or normalized)
    title_candidate_2 = constraint_title(conclusion_segment or title_candidate_1)
    title_candidate_3 = constraint_title(_extract_keyword_title(best_natural_segment or normalized))

    highlight_base = _pick_highlight_base(segments, normalized, best_natural_segment)
    highlight_candidate_1 = constraint_highlight(highlight_base)
    highlight_candidate_2 = constraint_highlight(
        _pick_sentence_by_tokens(segments, HIGHLIGHT_VERB_TOKENS, highlight_base)
    )
    highlight_candidate_3 = constraint_highlight(
        _pick_sentence_by_tokens(segments, HIGHLIGHT_COMPARE_TOKENS, highlight_base)
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