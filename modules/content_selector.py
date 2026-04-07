from typing import Dict, Any

from modules.content_candidate import generate_candidates
from modules.content_candidate_hybrid import generate_hybrid_candidate_bundle
from modules.content_ranking import rank_candidates


def select_best_content(raw_text: str, config: Dict[str, Any] | None = None) -> Dict[str, Any]:
    candidate_source = "rule"
    fallback_used = False

    if config is None:
        candidates = generate_candidates(raw_text)
    else:
        hybrid_selector_config = config.get("hybrid_selector", {}) if isinstance(config, dict) else {}
        ai_config = config.get("ai_candidate", {}) if isinstance(config, dict) else {}
        hybrid_enabled = hybrid_selector_config.get("enabled")
        if hybrid_enabled is None:
            hybrid_enabled = ai_config.get("enabled") is True

        if hybrid_enabled and ai_config.get("enabled") is True:
            try:
                bundle = generate_hybrid_candidate_bundle(raw_text, config)
                candidates = bundle.get("candidates", {})
                candidate_source = bundle.get("candidate_source", "rule")
                fallback_used = bool(bundle.get("fallback_used", False))
                if not candidates:
                    candidates = generate_candidates(raw_text)
                    candidate_source = "rule"
                    fallback_used = True
            except Exception:
                candidates = generate_candidates(raw_text)
                candidate_source = "rule"
                fallback_used = True
        else:
            candidates = generate_candidates(raw_text)

    ranked = rank_candidates(candidates)

    return {
        "title": ranked["best_title"],
        "highlight": ranked["best_highlight"],
        "debug": {
            "candidate_source": candidate_source,
            "fallback_used": fallback_used,
            "title_candidates": candidates.get("title_candidates", []),
            "highlight_candidates": candidates.get("highlight_candidates", []),
            "title_scores": ranked.get("title_scores", []),
            "highlight_scores": ranked.get("highlight_scores", []),
        },
    }