from typing import Dict, List


TITLE_BAD_ENDINGS = ["的", "了", "是", "在", "和", "呢"]
STRUCTURE_VERBS = ["是", "做", "让", "变", "决定", "影响"]
STRUCTURE_COMPARE_TOKENS = ["不是", "而是", "从", "到"]
HIGHLIGHT_BAD_FRAGMENTS = ["如果", "因为", "但是", "所以"]


def _safe_list(value: object) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item or "") for item in value]


def score_title(title: str) -> int:
    text = str(title or "")
    score = 0

    if 6 <= len(text) <= 16:
        score += 1

    if text and not any(text.endswith(token) for token in TITLE_BAD_ENDINGS):
        score += 1

    has_structure = any(token in text for token in STRUCTURE_VERBS) or any(
        token in text for token in STRUCTURE_COMPARE_TOKENS
    )
    if has_structure:
        score += 1

    return score


def score_highlight(highlight: str) -> int:
    text = str(highlight or "")
    score = 0

    if 4 <= len(text) <= 12:
        score += 1

    if any(token in text for token in STRUCTURE_VERBS):
        score += 1

    if not any(token in text for token in HIGHLIGHT_BAD_FRAGMENTS):
        score += 1

    return score


def _score_titles(title_candidates: List[str]) -> List[int]:
    return [score_title(title) for title in title_candidates]


def _score_highlights(highlight_candidates: List[str]) -> List[int]:
    return [score_highlight(highlight) for highlight in highlight_candidates]


def _pick_best(candidates: List[str], scores: List[int]) -> str:
    if not candidates:
        return ""

    best_index = 0
    best_score = scores[0] if scores else 0

    for index, score in enumerate(scores):
        if score > best_score:
            best_index = index
            best_score = score

    return candidates[best_index]


def rank_candidates(candidates: Dict[str, List[str]]) -> Dict[str, object]:
    title_candidates = _safe_list(candidates.get("title_candidates"))
    highlight_candidates = _safe_list(candidates.get("highlight_candidates"))

    title_scores = _score_titles(title_candidates)
    highlight_scores = _score_highlights(highlight_candidates)

    return {
        "best_title": _pick_best(title_candidates, title_scores),
        "best_highlight": _pick_best(highlight_candidates, highlight_scores),
        "title_scores": title_scores,
        "highlight_scores": highlight_scores,
    }