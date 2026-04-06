# -*- coding: utf-8 -*-
"""
modules/highlight_extractor.py

职责：
1. 优先从 scene 文案结构中提取 highlight 短语
2. 按 问题 / 方案 / 结果 的表达节点组织候选
3. 对候选做轻量 ranking，优先保留更有表达价值的短语
4. 提取不足时，回退到 raw_highlights 与 fallback_keywords
5. 任何异常都不向上抛出，保证视频渲染链安全
"""

from __future__ import annotations

import re
from typing import Iterable, List, Sequence


SENTENCE_SPLIT_PATTERN = re.compile(r"[。！？；!?;\n]+")
PHRASE_STRIP_PATTERN = re.compile(r"^[，、,：:；;\s]+|[，、,：:；;\s]+$")
INNER_SPACE_PATTERN = re.compile(r"\s+")

PROBLEM_PATTERNS = [
    re.compile(r"[^，。！？；]{2,24}?(?:效率低|成本高|门槛高|风险高|产能不足|不稳定|不一致|承压|受限|滞后|复杂|低效|停机风险|浪费)")
]
SOLUTION_SUBJECT_PATTERNS = [
    re.compile(r"(?:通过|借助|依靠)([^，。！？；]{2,18})"),
    re.compile(r"([^，。！？；]{2,18}?)(?:系统|方案|平台|产线|设备|能力|机制)(?=(?:可以|能够|可|用于|帮助|实现|提升|降低))"),
    re.compile(r"([^，。！？；]{2,18}?)(?:可以|能够|可|用于|帮助|让|使)")
]
RESULT_PATTERNS = [
    re.compile(r"(?:提升|提高|降低|减少|控制|缩短|增强|改善|优化|保持|实现|形成|带来|获得|避免)[^，。！？；]{2,20}"),
    re.compile(r"(?:更容易|更快|更稳定|更高效)[^，。！？；]{1,18}"),
]
STRUCTURE_PATTERNS = [
    re.compile(r"因为([^，。！？；]{2,18})所以([^，。！？；]{2,18})"),
    re.compile(r"虽然([^，。！？；]{2,18})但是([^，。！？；]{2,18})"),
    re.compile(r"不是([^，。！？；]{2,18})而是([^，。！？；]{2,18})"),
    re.compile(r"如果([^，。！？；]{2,18})就([^，。！？；]{2,18})"),
    re.compile(r"当([^，。！？；]{2,18})时([^，。！？；]{2,18})"),
    re.compile(r"通过([^，。！？；]{2,18})实现([^，。！？；]{2,18})"),
    re.compile(r"(?:最终|从而)([^，。！？；]{2,18})"),
]
STOPWORDS = {
    "我们",
    "你们",
    "他们",
    "这个",
    "这种",
    "因此",
    "所以",
    "因为",
    "如果",
    "可以",
    "能够",
    "然后",
    "最后",
    "以及",
    "同时",
    "继续观看",
}
RESULT_ACTION_WORDS = (
    "提升",
    "提高",
    "降低",
    "减少",
    "改善",
    "优化",
    "增强",
    "实现",
    "保持",
    "形成",
    "带来",
    "缩短",
    "控制",
    "避免",
    "获得",
)
SOLUTION_ENTITY_WORDS = (
    "系统",
    "方案",
    "设备",
    "机制",
    "产线",
    "自动化",
    "平台",
    "能力",
)
PROBLEM_SIGNAL_WORDS = (
    "效率低",
    "成本高",
    "风险高",
    "不稳定",
    "不一致",
    "受限",
    "停机风险",
    "复杂",
    "低效",
    "承压",
    "门槛高",
    "产能不足",
)
WEAK_GENERIC_WORDS = {
    "效率",
    "成本",
    "稳定",
    "结果",
    "价值",
    "信息",
    "变化",
    "方案",
    "系统",
    "结论",
}
WEAK_STOP_PHRASES = {
    "因为",
    "所以",
    "如果",
    "最终",
    "然后",
    "同时",
    "我们",
    "这个",
    "这种",
}


def _clean_text(text: str) -> str:
    normalized = str(text or "").replace("\r", " ").strip()
    return INNER_SPACE_PATTERN.sub("", normalized)


def _split_sentences(text: str) -> List[str]:
    cleaned = _clean_text(text)
    if not cleaned:
        return []
    return [item.strip() for item in SENTENCE_SPLIT_PATTERN.split(cleaned) if item and item.strip()]


def _normalize_phrase(phrase: str) -> str:
    cleaned = PHRASE_STRIP_PATTERN.sub("", str(phrase or "").strip())
    cleaned = cleaned.strip("“”\"'（）()[]【】")
    return cleaned


def _comparable_phrase(phrase: str) -> str:
    cleaned = _normalize_phrase(phrase)
    return re.sub(r"[，。！？；、,.!?;:：\-\s]", "", cleaned)


def _char_bigrams(text: str) -> set[str]:
    if len(text) < 2:
        return {text} if text else set()
    return {text[index:index + 2] for index in range(len(text) - 1)}


def _overlap_ratio(left: str, right: str) -> float:
    left_cmp = _comparable_phrase(left)
    right_cmp = _comparable_phrase(right)
    if not left_cmp or not right_cmp:
        return 0.0
    if left_cmp in right_cmp or right_cmp in left_cmp:
        shorter = min(len(left_cmp), len(right_cmp))
        longer = max(len(left_cmp), len(right_cmp))
        if longer == 0:
            return 0.0
        return shorter / longer

    left_tokens = _char_bigrams(left_cmp)
    right_tokens = _char_bigrams(right_cmp)
    if not left_tokens or not right_tokens:
        return 0.0
    intersection = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    if union <= 0:
        return 0.0
    return intersection / union


def _is_valid_phrase(phrase: str) -> bool:
    cleaned = _normalize_phrase(phrase)
    if not cleaned:
        return False
    if cleaned in STOPWORDS:
        return False
    if len(cleaned) < 2:
        return False
    if len(cleaned) > 24:
        return False
    return True


def _is_weak_generic_phrase(phrase: str) -> bool:
    cleaned = _normalize_phrase(phrase)
    if not cleaned:
        return True
    if cleaned in WEAK_GENERIC_WORDS or cleaned in WEAK_STOP_PHRASES:
        return True
    if len(cleaned) <= 2:
        return True
    return False


def _append_unique(items: List[str], phrase: str, max_items: int) -> None:
    cleaned = _normalize_phrase(phrase)
    if not _is_valid_phrase(cleaned):
        return

    comparable = cleaned.replace("，", "").replace("。", "")
    for existing in items:
        existing_comp = existing.replace("，", "").replace("。", "")
        if comparable == existing_comp:
            return
        if comparable in existing_comp or existing_comp in comparable:
            if len(comparable) <= len(existing_comp):
                return
    items.append(cleaned)
    if len(items) > max_items:
        del items[max_items:]


def score_highlight_phrase(phrase: str, scene_text: str = "") -> int:
    cleaned = _normalize_phrase(phrase)
    if not _is_valid_phrase(cleaned):
        return -100

    score = 0
    length = len(cleaned)
    if 4 <= length <= 12:
        score += 6
    elif 3 <= length <= 14:
        score += 3
    elif length <= 2:
        score -= 8
    elif length >= 18:
        score -= 4

    if any(word in cleaned for word in RESULT_ACTION_WORDS):
        score += 9
    if any(word in cleaned for word in SOLUTION_ENTITY_WORDS):
        score += 7
    if any(word in cleaned for word in PROBLEM_SIGNAL_WORDS):
        score += 7

    if any(word in cleaned for word in WEAK_STOP_PHRASES):
        score -= 10
    if cleaned in WEAK_GENERIC_WORDS:
        score -= 8
    elif _is_weak_generic_phrase(cleaned):
        score -= 4

    if re.search(r"\d", cleaned):
        score += 2

    normalized_scene = _clean_text(scene_text)
    if cleaned and normalized_scene and cleaned in normalized_scene:
        score += 2
        start_index = normalized_scene.find(cleaned)
        if 0 <= start_index <= max(0, len(normalized_scene) // 2):
            score += 1

    if re.search(r"(?:提升|提高|降低|减少|改善|优化|增强|实现|保持|形成|带来|缩短|控制|避免).{1,8}", cleaned):
        score += 2

    return score


def rank_highlights(
    phrases: List[str],
    scene_text: str = "",
    max_items: int = 3,
) -> List[str]:
    """对候选 highlight 做轻量打分与去重，失败时回退原顺序。"""
    try:
        normalized_candidates: List[str] = []
        for phrase in phrases:
            cleaned = _normalize_phrase(phrase)
            if not _is_valid_phrase(cleaned):
                continue
            if cleaned in normalized_candidates:
                continue
            normalized_candidates.append(cleaned)

        if len(normalized_candidates) <= 1:
            return normalized_candidates[:max_items]

        scored_candidates = []
        for index, phrase in enumerate(normalized_candidates):
            score = score_highlight_phrase(phrase, scene_text=scene_text)
            scored_candidates.append((phrase, score, index))

        scored_candidates.sort(key=lambda item: (-item[1], -len(item[0]), item[2]))

        selected: List[str] = []
        selected_scores: List[int] = []
        for phrase, score, _ in scored_candidates:
            replaced = False
            skip_current = False

            for selected_index, existing in enumerate(selected):
                overlap = _overlap_ratio(phrase, existing)
                if overlap < 0.56:
                    continue

                existing_score = selected_scores[selected_index]
                better_phrase = score > existing_score or (
                    score == existing_score and len(phrase) > len(existing)
                )
                if better_phrase:
                    selected[selected_index] = phrase
                    selected_scores[selected_index] = score
                    replaced = True
                else:
                    skip_current = True
                break

            if skip_current:
                continue
            if replaced:
                continue

            selected.append(phrase)
            selected_scores.append(score)
            if len(selected) >= max_items:
                break

        return selected[:max_items]
    except Exception:
        fallback_results: List[str] = []
        for phrase in phrases:
            cleaned = _normalize_phrase(phrase)
            if not _is_valid_phrase(cleaned):
                continue
            if cleaned in fallback_results:
                continue
            fallback_results.append(cleaned)
            if len(fallback_results) >= max_items:
                break
        return fallback_results


def _extend_ranked_group(
    selected: List[str],
    candidates: List[str],
    scene_text: str,
    max_items: int,
) -> List[str]:
    if len(selected) >= max_items:
        return selected[:max_items]

    ranked = rank_highlights(candidates, scene_text=scene_text, max_items=max_items)
    for phrase in ranked:
        if any(_overlap_ratio(phrase, existing) >= 0.56 for existing in selected):
            continue
        selected.append(phrase)
        if len(selected) >= max_items:
            break
    return selected[:max_items]


def _collect_pattern_matches(sentence: str, patterns: Sequence[re.Pattern[str]], max_items: int) -> List[str]:
    results: List[str] = []
    for pattern in patterns:
        for match in pattern.finditer(sentence):
            groups = [group for group in match.groups() if group]
            if groups:
                for group in groups:
                    _append_unique(results, group, max_items)
            else:
                _append_unique(results, match.group(0), max_items)
            if len(results) >= max_items:
                return results
    return results


def extract_problem_phrases(scene_text: str, max_items: int = 2) -> List[str]:
    results: List[str] = []
    for sentence in _split_sentences(scene_text):
        for phrase in _collect_pattern_matches(sentence, PROBLEM_PATTERNS, max_items=max_items):
            _append_unique(results, phrase, max_items)
        if "而" in sentence:
            left_part = sentence.split("而", 1)[0]
            if re.search(r"低|高|慢|难|不足|承压|受限|风险|问题|瓶颈|停机", left_part):
                _append_unique(results, left_part, max_items)
        if len(results) >= max_items:
            break
    return results


def extract_solution_phrases(scene_text: str, max_items: int = 2) -> List[str]:
    results: List[str] = []
    for sentence in _split_sentences(scene_text):
        for phrase in _collect_pattern_matches(sentence, SOLUTION_SUBJECT_PATTERNS, max_items=max_items):
            _append_unique(results, phrase, max_items)
        for structure in STRUCTURE_PATTERNS:
            matched = structure.search(sentence)
            if not matched:
                continue
            groups = [group for group in matched.groups() if group]
            if structure.pattern.startswith("通过") and groups:
                _append_unique(results, groups[0], max_items)
        if len(results) >= max_items:
            break
    return results


def extract_result_phrases(scene_text: str, max_items: int = 3) -> List[str]:
    results: List[str] = []
    for sentence in _split_sentences(scene_text):
        for phrase in _collect_pattern_matches(sentence, RESULT_PATTERNS, max_items=max_items):
            _append_unique(results, phrase, max_items)
        for structure in STRUCTURE_PATTERNS:
            matched = structure.search(sentence)
            if not matched:
                continue
            groups = [group for group in matched.groups() if group]
            if groups:
                _append_unique(results, groups[-1], max_items)
        if len(results) >= max_items:
            break
    return results


def merge_and_dedup(*groups: Iterable[str], max_items: int = 3) -> List[str]:
    results: List[str] = []
    for group in groups:
        for phrase in group:
            _append_unique(results, phrase, max_items)
            if len(results) >= max_items:
                return results
    return results


def extract_structured_highlights(
    scene_text: str,
    raw_highlights: List[str] | None = None,
    fallback_keywords: List[str] | None = None,
    max_items: int = 3,
) -> List[str]:
    """优先从文案结构提取 highlight，不足时再补旧字段与 fallback。"""
    try:
        normalized_text = _clean_text(scene_text)
        normalized_raw = [str(item or "").strip() for item in list(raw_highlights or [])]
        normalized_fallback = [str(item or "").strip() for item in list(fallback_keywords or [])]
        merge_limit = max(12, max_items * 4)

        if not normalized_text:
            selected = []
            selected = _extend_ranked_group(selected, normalized_raw, normalized_text, max_items)
            selected = _extend_ranked_group(selected, normalized_fallback, normalized_text, max_items)
            return selected[:max_items]

        extraction_limit = max(4, max_items * 2)
        problem_phrases = extract_problem_phrases(normalized_text, max_items=extraction_limit)
        solution_phrases = extract_solution_phrases(normalized_text, max_items=extraction_limit)
        result_phrases = extract_result_phrases(normalized_text, max_items=extraction_limit)

        structured = merge_and_dedup(
            problem_phrases,
            solution_phrases,
            result_phrases,
            max_items=merge_limit,
        )
        selected = []
        selected = _extend_ranked_group(selected, structured, normalized_text, max_items)
        selected = _extend_ranked_group(selected, normalized_raw, normalized_text, max_items)
        selected = _extend_ranked_group(selected, normalized_fallback, normalized_text, max_items)
        return selected[:max_items]
    except Exception:
        selected = []
        selected = _extend_ranked_group(selected, list(raw_highlights or []), str(scene_text or ""), max_items)
        selected = _extend_ranked_group(selected, list(fallback_keywords or []), str(scene_text or ""), max_items)
        return selected[:max_items]