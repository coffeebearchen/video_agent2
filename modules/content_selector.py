from typing import Dict, Any

from modules.content_candidate import generate_candidates
from modules.content_ranking import rank_candidates


def select_best_content(raw_text: str) -> Dict[str, Any]:
    candidates = generate_candidates(raw_text)
    ranked = rank_candidates(candidates)

    return {
        "title": ranked["best_title"],
        "highlight": ranked["best_highlight"],
        "debug": {
            "title_candidates": candidates.get("title_candidates", []),
            "highlight_candidates": candidates.get("highlight_candidates", []),
            "title_scores": ranked.get("title_scores", []),
            "highlight_scores": ranked.get("highlight_scores", []),
        },
    }