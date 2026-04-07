from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from modules.highlight_extractor import (
    extract_problem_phrases,
    extract_result_phrases,
    extract_solution_phrases,
    extract_structured_highlights,
    rank_highlights,
)
from modules.overlay_style_engine import get_highlight_spec, resolve_highlight_timing


SENTENCE_SPLIT_PATTERN = re.compile(r"[。！？!?；;\n]+")
CLAUSE_SPLIT_PATTERN = re.compile(r"[，,、\n]+")
SPACE_PATTERN = re.compile(r"\s+")
LEADING_CONNECTOR_PATTERN = re.compile(r"^(?:而且|而是|而|但|但是|同时|所以|因此|其实|最后|并且|并|真正|关键是|重点是|核心是)+")
TITLE_FILLER_PATTERN = re.compile(r"(?:可以|能够|有效|显著|往往|通常|还可|还能|有助于|帮助|通过|实现了?)")
HIGHLIGHT_FILLER_PATTERN = re.compile(r"^(?:要么是|就是|其实是|重点是|关键是|真正是)")
RESULT_WORDS = ("提升", "提高", "降低", "减少", "改善", "优化", "增强", "实现", "保持", "形成", "带来", "缩短", "控制", "避免", "稳定")
ENTITY_WORDS = ("自动化", "系统", "方案", "产线", "设备", "平台", "能力", "控制")
PROBLEM_WORDS = ("效率低", "成本高", "风险高", "停机风险", "低效", "不稳定", "误差", "压力")
THEME_CUES = ("核心", "关键", "重点", "本质", "真正")
LATE_FOCUS_CUES = ("但是", "真正", "关键", "重点", "核心", "本质", "而是", "所以", "最后", "其实")
WEAK_GENERIC_WORDS = {"效率", "成本", "稳定", "系统", "方案", "结果", "价值", "信息", "变化"}
STRUCTURE_PATTERNS = (
    re.compile(r"不是[^，。！？；]{1,18}而是([^，。！？；]{2,18})"),
    re.compile(r"虽然[^，。！？；]{1,18}但是([^，。！？；]{2,18})"),
    re.compile(r"因为[^，。！？；]{1,18}所以([^，。！？；]{2,18})"),
    re.compile(r"通过[^，。！？；]{1,18}实现([^，。！？；]{2,18})"),
)


def _clean_text(text: str) -> str:
    normalized = str(text or "").replace("\r", " ").strip()
    return SPACE_PATTERN.sub("", normalized)


def _split_sentences(text: str) -> List[str]:
    cleaned = _clean_text(text)
    if not cleaned:
        return []
    return [item.strip() for item in SENTENCE_SPLIT_PATTERN.split(cleaned) if item and item.strip()]


def _normalize_phrase(text: str) -> str:
    cleaned = str(text or "").strip().strip("，。！？；、,.!?;:：\"'“”‘’（）()[]【】")
    cleaned = LEADING_CONNECTOR_PATTERN.sub("", cleaned)
    return cleaned.strip()


def _comparable_text(text: str) -> str:
    return re.sub(r"[，。！？；、,.!?;:：\-\s]", "", _normalize_phrase(text))


def _truncate(text: str, max_chars: int) -> str:
    cleaned = _normalize_phrase(text)
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rstrip()


def _dedupe(items: List[str]) -> List[str]:
    results: List[str] = []
    seen = set()
    for item in items:
        cleaned = _normalize_phrase(item)
        comparable = _comparable_text(cleaned)
        if not cleaned or not comparable or comparable in seen:
            continue
        seen.add(comparable)
        results.append(cleaned)
    return results


def _score_semantic_phrase(text: str, scene_text: str, prefer_theme: bool = False) -> int:
    cleaned = _normalize_phrase(text)
    if not cleaned:
        return -100

    score = 0
    length = len(cleaned)
    if 5 <= length <= 14:
        score += 8
    elif 4 <= length <= 18:
        score += 4
    elif length <= 2:
        score -= 10
    elif length >= 20:
        score -= 4

    if any(word in cleaned for word in RESULT_WORDS):
        score += 9
    if any(word in cleaned for word in ENTITY_WORDS):
        score += 6
    if any(word in cleaned for word in THEME_CUES):
        score += 3
    if any(word in cleaned for word in PROBLEM_WORDS):
        score += 2
    if cleaned in WEAK_GENERIC_WORDS:
        score -= 8

    normalized_scene = _clean_text(scene_text)
    if cleaned and normalized_scene and cleaned in normalized_scene:
        score += 2
        hit_index = normalized_scene.find(cleaned)
        if hit_index >= max(0, int(len(normalized_scene) * 0.4)):
            score += 2

    if prefer_theme and any(word in cleaned for word in ENTITY_WORDS):
        score += 4

    return score


def _best_clause(text: str, scene_text: str, prefer_theme: bool = False) -> str:
    clauses = [_normalize_phrase(part) for part in CLAUSE_SPLIT_PATTERN.split(str(text or ""))]
    clauses = [clause for clause in clauses if clause]
    if not clauses:
        return _normalize_phrase(text)

    scored = sorted(
        clauses,
        key=lambda item: (_score_semantic_phrase(item, scene_text, prefer_theme=prefer_theme), -abs(len(item) - 10), len(item)),
        reverse=True,
    )
    return scored[0]


def _compress_title(text: str, max_chars: int) -> str:
    cleaned = _normalize_phrase(text)
    cleaned = TITLE_FILLER_PATTERN.sub("", cleaned)
    cleaned = re.sub(r"(?:之后|以后|过程中|这个时候)$", "", cleaned)
    cleaned = cleaned.strip()

    if len(cleaned) > max_chars:
        cleaned = _best_clause(cleaned, cleaned, prefer_theme=True)
    return _truncate(cleaned, max_chars)


def _compress_highlight(text: str, max_chars: int) -> str:
    cleaned = _normalize_phrase(text)
    cleaned = HIGHLIGHT_FILLER_PATTERN.sub("", cleaned)
    cleaned = cleaned.strip()

    if len(cleaned) > max_chars:
        cleaned = _best_clause(cleaned, cleaned)
    return _truncate(cleaned, max_chars)


def _collect_title_candidates(scene_text: str, scene_highlights: List[str], max_chars: int) -> List[Tuple[str, str]]:
    candidates: List[Tuple[str, str]] = []
    solution_phrases = extract_solution_phrases(scene_text, max_items=3)
    result_phrases = extract_result_phrases(scene_text, max_items=3)
    structured = extract_structured_highlights(scene_text, raw_highlights=scene_highlights, max_items=3)
    sentences = _split_sentences(scene_text)

    if solution_phrases and result_phrases:
        candidates.append(("solution_result", _compress_title(f"{solution_phrases[0]}{result_phrases[0]}", max_chars)))
    if result_phrases:
        candidates.append(("result_phrase", _compress_title(result_phrases[0], max_chars)))
    if solution_phrases:
        candidates.append(("solution_phrase", _compress_title(solution_phrases[0], max_chars)))
    if structured:
        candidates.append(("structured", _compress_title(structured[0], max_chars)))

    for sentence in sentences[:3]:
        candidates.append(("sentence_focus", _compress_title(_best_clause(sentence, scene_text, prefer_theme=True), max_chars)))

    if sentences:
        candidates.append(("first_sentence", _compress_title(sentences[0], max_chars)))
    candidates.append(("scene_text", _compress_title(scene_text, max_chars)))
    return [(source, text) for source, text in candidates if text]


def _collect_highlight_candidates(scene_text: str, scene_highlights: List[str], max_chars: int) -> List[Tuple[str, str]]:
    candidates: List[Tuple[str, str]] = []
    provided = _dedupe([str(item or "").strip() for item in scene_highlights or []])
    structured = extract_structured_highlights(scene_text, raw_highlights=provided, max_items=5)
    result_phrases = extract_result_phrases(scene_text, max_items=4)
    solution_phrases = extract_solution_phrases(scene_text, max_items=3)
    problem_phrases = extract_problem_phrases(scene_text, max_items=2)

    for phrase in result_phrases:
        candidates.append(("result_phrase", _compress_highlight(phrase, max_chars)))
    for phrase in structured:
        candidates.append(("structured", _compress_highlight(phrase, max_chars)))
    for phrase in provided:
        candidates.append(("provided_highlight", _compress_highlight(phrase, max_chars)))
    for phrase in solution_phrases:
        candidates.append(("solution_phrase", _compress_highlight(phrase, max_chars)))
    for phrase in problem_phrases:
        candidates.append(("problem_phrase", _compress_highlight(phrase, max_chars)))

    extracted_focus: List[str] = []
    for pattern in STRUCTURE_PATTERNS:
        for sentence in _split_sentences(scene_text):
            match = pattern.search(sentence)
            if match and match.group(1):
                extracted_focus.append(match.group(1))
    for phrase in extracted_focus:
        candidates.append(("structure_focus", _compress_highlight(phrase, max_chars)))

    return [(source, text) for source, text in candidates if text]


def _pick_highlight(scene_text: str, scene_highlights: List[str], max_chars: int) -> Tuple[str, str]:
    candidates = _collect_highlight_candidates(scene_text, scene_highlights, max_chars)
    if not candidates:
        return "none", ""

    unique_texts = _dedupe([text for _, text in candidates])
    ranked = rank_highlights(unique_texts, scene_text=scene_text, max_items=max(len(unique_texts), 1))
    rank_bonus_map = {text: max(0, (len(ranked) - index) * 4) for index, text in enumerate(ranked)}
    source_bonus = {
        "result_phrase": 12,
        "structure_focus": 10,
        "structured": 8,
        "provided_highlight": 6,
        "solution_phrase": 5,
        "problem_phrase": 3,
    }

    best_source = "none"
    best_text = ""
    best_score = -10_000
    seen = set()
    for source, text in candidates:
        comparable = _comparable_text(text)
        if not comparable or comparable in seen:
            continue
        seen.add(comparable)
        score = _score_semantic_phrase(text, scene_text) + source_bonus.get(source, 0) + rank_bonus_map.get(text, 0)
        if score > best_score:
            best_score = score
            best_source = source
            best_text = text
    return best_source, best_text


def _pick_title(scene_text: str, scene_highlights: List[str], highlight_text: str, max_chars: int) -> Tuple[str, str]:
    candidates = _collect_title_candidates(scene_text, scene_highlights, max_chars)
    if not candidates:
        return "none", ""

    highlight_cmp = _comparable_text(highlight_text)
    best_source = "none"
    best_text = ""
    best_score = -10_000
    seen = set()
    source_bonus = {
        "solution_result": 13,
        "result_phrase": 8,
        "solution_phrase": 7,
        "sentence_focus": 5,
        "structured": 4,
        "first_sentence": 3,
        "scene_text": 1,
    }

    for source, text in candidates:
        comparable = _comparable_text(text)
        if not comparable or comparable in seen:
            continue
        seen.add(comparable)
        score = _score_semantic_phrase(text, scene_text, prefer_theme=True) + source_bonus.get(source, 0)
        if highlight_cmp and (comparable == highlight_cmp or comparable in highlight_cmp or highlight_cmp in comparable):
            score -= 7
        if score > best_score:
            best_score = score
            best_source = source
            best_text = text
    return best_source, best_text


def _clamp_window(start: float, desired_duration: float, total_duration: float) -> Tuple[float, float]:
    safe_total = max(0.1, float(total_duration or 0.0))
    max_start = max(0.0, safe_total - 0.5)
    safe_start = max(0.0, min(float(start or 0.0), max_start))
    min_duration = min(0.8, safe_total)
    safe_duration = max(min_duration, min(float(desired_duration or 0.0), max(min_duration, safe_total - safe_start)))
    return safe_start, safe_duration


def _find_focus_ratio(scene_text: str, highlight_text: str, base_ratio: float, semantic_min_ratio: float, semantic_max_ratio: float) -> Tuple[float, str]:
    normalized_scene = _clean_text(scene_text)
    normalized_highlight = _clean_text(highlight_text)
    if not normalized_scene:
        return base_ratio, "base_fixed"

    candidate_ratio = base_ratio
    timing_mode = "base_fixed"

    if normalized_highlight and normalized_highlight in normalized_scene:
        position = normalized_scene.find(normalized_highlight)
        phrase_ratio = (position + max(1, len(normalized_highlight)) * 0.4) / max(1, len(normalized_scene))
        phrase_ratio = min(semantic_max_ratio, max(base_ratio, phrase_ratio + 0.05))
        if phrase_ratio > candidate_ratio:
            candidate_ratio = phrase_ratio
            timing_mode = "phrase_position"

    cue_positions = [normalized_scene.find(cue) for cue in LATE_FOCUS_CUES if cue in normalized_scene]
    cue_positions = [position for position in cue_positions if position >= 0]
    if cue_positions:
        cue_ratio = (max(cue_positions) / max(1, len(normalized_scene))) + 0.06
        cue_ratio = min(semantic_max_ratio, max(semantic_min_ratio, cue_ratio, base_ratio))
        if cue_ratio > candidate_ratio:
            candidate_ratio = cue_ratio
            timing_mode = "semantic_late_shift"

    return candidate_ratio, timing_mode


def resolve_aligned_highlight_timing(
    scene_duration: float,
    scene_text: str,
    highlight_text: str,
    style_name: str,
) -> Tuple[float, float, str]:
    base_start, base_duration = resolve_highlight_timing(scene_duration, style_name=style_name)
    highlight_spec = get_highlight_spec(style_name)
    safe_scene_duration = max(0.1, float(scene_duration or 0.0))
    base_ratio = max(
        float(highlight_spec.get("start_ratio", 0.35) or 0.35),
        base_start / safe_scene_duration,
    )
    semantic_min_ratio = float(highlight_spec.get("semantic_min_ratio", 0.45) or 0.45)
    semantic_max_ratio = float(highlight_spec.get("semantic_max_ratio", 0.6) or 0.6)

    if not highlight_text:
        start, duration = _clamp_window(base_start, base_duration, safe_scene_duration)
        return start, duration, "base_fixed"

    focus_ratio, timing_mode = _find_focus_ratio(
        scene_text=scene_text,
        highlight_text=highlight_text,
        base_ratio=base_ratio,
        semantic_min_ratio=semantic_min_ratio,
        semantic_max_ratio=semantic_max_ratio,
    )
    start = max(float(highlight_spec.get("min_start", 0.8) or 0.8), safe_scene_duration * focus_ratio)
    start, duration = _clamp_window(start, base_duration, safe_scene_duration)
    return start, duration, timing_mode


def align_scene_expression(
    scene_id: int,
    scene_text: str,
    scene_highlights: List[str],
    scene_duration: float,
    style_name: str,
    title_max_chars: int = 20,
    highlight_max_chars: int = 18,
) -> Dict[str, Any]:
    highlight_source, highlight_final = _pick_highlight(scene_text, scene_highlights, highlight_max_chars)
    title_source, title_final = _pick_title(scene_text, scene_highlights, highlight_final, title_max_chars)
    highlight_start, highlight_duration, timing_mode = resolve_aligned_highlight_timing(
        scene_duration=scene_duration,
        scene_text=scene_text,
        highlight_text=highlight_final,
        style_name=style_name,
    )

    return {
        "scene_id": scene_id,
        "title_source": title_source,
        "title_final": title_final,
        "highlight_source": highlight_source,
        "highlight_final": highlight_final,
        "timing_mode": timing_mode,
        "highlight_start": highlight_start,
        "highlight_duration": highlight_duration,
    }


def emit_expression_alignment_logs(alignment_result: Dict[str, Any]) -> None:
    print(f"[EXPR_ALIGN] scene_id={alignment_result.get('scene_id')}")
    print(f"[EXPR_ALIGN] title_source={alignment_result.get('title_source', 'none')}")
    print(f"[EXPR_ALIGN] title_final={alignment_result.get('title_final', '')}")
    print(f"[EXPR_ALIGN] highlight_source={alignment_result.get('highlight_source', 'none')}")
    print(f"[EXPR_ALIGN] highlight_final={alignment_result.get('highlight_final', '')}")
    print(f"[EXPR_ALIGN] timing_mode={alignment_result.get('timing_mode', 'base_fixed')}")
    print(f"[EXPR_ALIGN] highlight_start={float(alignment_result.get('highlight_start', 0.0)):.2f}")
    print(f"[EXPR_ALIGN] highlight_duration={float(alignment_result.get('highlight_duration', 0.0)):.2f}")