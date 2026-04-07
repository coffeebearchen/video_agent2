import re
from typing import Any, Dict, List, Optional

from modules.content_candidate import generate_candidates
from modules.content_candidate_deepseek import generate_ai_candidates
from modules.content_constraints import constrain_highlight_zh, constrain_title_text


AI_TITLE_PREFIXES = ["为什么", "如何", "到底", "其实", "真的", "是否"]
AI_TITLE_WEAK_TOKENS = ["立刻", "其实", "真的", "完全", "非常"]
AI_TITLE_SHORTEN_MAP = {
    "市场预期": "预期",
    "如何影响": "影响",
    "为什么影响": "影响",
    "如何决定": "决定",
    "为什么决定": "决定",
    "股市立刻上涨": "股市上涨",
    "立刻上涨": "上涨",
}
AI_HIGHLIGHT_WEAK_TOKENS = ["立刻", "其实", "真的", "完全", "非常"]
AI_HIGHLIGHT_SHORTEN_MAP = {
    "市场预期": "预期",
    "取决于市场预期": "取决于预期",
    "贴现率": "贴现",
}
AI_CONTRAST_MARKERS = ["不是", "而是", "不等于"]


def _normalize_text(text: str) -> str:
    return str(text or "").replace(" ", "").strip()


def _replace_once(text: str, old: str, new: str) -> str:
    if old and old in text:
        return text.replace(old, new, 1)
    return text


def _dedupe_preserve_order(items: List[str]) -> List[str]:
    seen = set()
    result: List[str] = []

    for item in items:
        normalized = _normalize_text(item)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(item)

    return result


def _candidates_equal(left: Dict[str, List[str]], right: Dict[str, List[str]]) -> bool:
    return (
        left.get("title_candidates", []) == right.get("title_candidates", [])
        and left.get("highlight_candidates", []) == right.get("highlight_candidates", [])
    )


def tighten_ai_title(text: str) -> str:
    tightened = constrain_title_text(text)
    if not tightened:
        return ""

    for prefix in AI_TITLE_PREFIXES:
        if tightened.startswith(prefix) and len(tightened) - len(prefix) >= 6:
            tightened = tightened[len(prefix):]
            break

    for old, new in AI_TITLE_SHORTEN_MAP.items():
        if len(tightened) <= 8:
            break
        tightened = _replace_once(tightened, old, new)

    for token in AI_TITLE_WEAK_TOKENS:
        if len(tightened) <= 10:
            break
        tightened = _replace_once(tightened, token, "")

    if len(tightened) > 8 or "如何" in tightened or "为什么" in tightened or "是否" in tightened:
        tightened = tightened.replace("如何", "")
        tightened = tightened.replace("为什么", "")
        tightened = tightened.replace("是否", "")

    tightened = re.sub(r"^(为什么|如何|到底|其实|真的|是否)", "", tightened)
    tightened = constrain_title_text(tightened)

    if len(tightened) > 10:
        tightened = constrain_title_text(tightened[:12])

    return tightened


def tighten_ai_highlight(text: str) -> str:
    tightened = constrain_highlight_zh(text)
    if not tightened:
        return ""

    for old, new in AI_HIGHLIGHT_SHORTEN_MAP.items():
        if len(tightened) <= 8:
            break
        tightened = _replace_once(tightened, old, new)

    for token in AI_HIGHLIGHT_WEAK_TOKENS:
        if len(tightened) <= 8:
            break
        tightened = _replace_once(tightened, token, "")

    if "都会" in tightened and len(tightened) > 10:
        anchor = tightened.find("都会")
        if anchor != -1:
            tightened = tightened[:anchor + len("都会")]

    tightened = constrain_highlight_zh(tightened)

    if any(marker in tightened for marker in AI_CONTRAST_MARKERS) and len(tightened) > 12:
        tightened = tightened[:12]
        tightened = constrain_highlight_zh(tightened)

    return tightened


def _normalize_ai_candidates(ai_candidates: Optional[Dict[str, List[str]]]) -> Optional[Dict[str, List[str]]]:
    if not ai_candidates:
        return None

    title_candidates = [
        tighten_ai_title(candidate)
        for candidate in ai_candidates.get("title_candidates", [])
        if str(candidate or "").strip()
    ]
    highlight_candidates = [
        tighten_ai_highlight(candidate)
        for candidate in ai_candidates.get("highlight_candidates", [])
        if str(candidate or "").strip()
    ]

    title_candidates = _dedupe_preserve_order([candidate for candidate in title_candidates if candidate])
    highlight_candidates = _dedupe_preserve_order([candidate for candidate in highlight_candidates if candidate])

    if not title_candidates or not highlight_candidates:
        return None

    return {
        "title_candidates": title_candidates,
        "highlight_candidates": highlight_candidates,
    }


def generate_hybrid_candidate_bundle(raw_text: str, config: Dict[str, Any]) -> Dict[str, Any]:
    rule = generate_candidates(raw_text)
    ai_config = config.get("ai_candidate", {}) if isinstance(config, dict) else {}

    if ai_config.get("enabled") is True and ai_config.get("provider") == "deepseek":
        try:
            ai = _normalize_ai_candidates(generate_ai_candidates(raw_text))
        except Exception:
            ai = None

        if ai is not None:
            merged = {
                "title_candidates": _dedupe_preserve_order(rule["title_candidates"] + ai["title_candidates"]),
                "highlight_candidates": _dedupe_preserve_order(rule["highlight_candidates"] + ai["highlight_candidates"]),
            }
            return {
                "candidates": merged,
                "candidate_source": "hybrid",
                "fallback_used": False,
            }

    return {
        "candidates": rule,
        "candidate_source": "rule",
        "fallback_used": ai_config.get("enabled") is True,
    }


def generate_hybrid_candidates(raw_text: str, config: Dict[str, Any]) -> Dict[str, List[str]]:
    return generate_hybrid_candidate_bundle(raw_text, config)["candidates"]