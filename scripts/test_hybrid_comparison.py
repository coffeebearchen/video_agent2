from pathlib import Path
import json
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.content_selector import select_best_content


CONFIG_PATH = PROJECT_ROOT / "config.json"
RAW_TEXT = "利率是资金的价格，资产价格会随着贴现率变化，不是所有降息都会立刻推动股市上涨，而是取决于市场预期和盈利修复。"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def normalize_text(text: str) -> str:
    return str(text or "").replace(" ", "").strip()


def shorten(text: str, limit: int = 30) -> str:
    value = str(text or "")
    if len(value) <= limit:
        return value
    return value[:limit] + "..."


def print_candidates(title: str, candidates: list[str], scores: list[int]) -> None:
    print(title)
    for index, candidate in enumerate(candidates):
        score = scores[index] if index < len(scores) else 0
        print(f"[{index}] {shorten(candidate)} (score: {score})")
    print()


def find_top_extra_candidate(rule_candidates: list[str], hybrid_candidates: list[str], hybrid_scores: list[int]) -> tuple[str, int]:
    rule_set = {normalize_text(item) for item in rule_candidates}
    best_text = ""
    best_score = -1

    for index, candidate in enumerate(hybrid_candidates):
        normalized = normalize_text(candidate)
        if normalized in rule_set:
            continue
        score = hybrid_scores[index] if index < len(hybrid_scores) else 0
        if score > best_score:
            best_text = candidate
            best_score = score

    if best_score < 0:
        return "", 0

    return best_text, best_score


def build_likely_reason(rule_result: dict, hybrid_result: dict) -> str:
    rule_debug = rule_result["debug"]
    hybrid_debug = hybrid_result["debug"]

    if hybrid_debug.get("fallback_used"):
        return "hybrid fallback triggered, rule path remained active"

    if rule_result["title"] != hybrid_result["title"] or rule_result["highlight"] != hybrid_result["highlight"]:
        return "hybrid candidates changed final selection after ranking"

    top_ai_title, top_ai_title_score = find_top_extra_candidate(
        rule_debug["title_candidates"],
        hybrid_debug["title_candidates"],
        hybrid_debug["title_scores"],
    )
    top_ai_highlight, top_ai_highlight_score = find_top_extra_candidate(
        rule_debug["highlight_candidates"],
        hybrid_debug["highlight_candidates"],
        hybrid_debug["highlight_scores"],
    )

    if top_ai_title or top_ai_highlight:
        if top_ai_highlight_score >= top_ai_title_score:
            return "ai highlight entered competition but lost on current ranking preference"
        return "ai title entered competition but lost on score"

    return "hybrid improved candidate diversity but not final selection"


base_config = load_config()
rule_config = dict(base_config)
rule_config["hybrid_selector"] = {"enabled": False}

hybrid_config = dict(base_config)
hybrid_config["hybrid_selector"] = {"enabled": True}
hybrid_config["ai_candidate"] = dict(base_config.get("ai_candidate", {}))
hybrid_config["ai_candidate"]["enabled"] = True

rule_result = select_best_content(RAW_TEXT, config=rule_config)
hybrid_result = select_best_content(RAW_TEXT, config=hybrid_config)

rule_debug = rule_result["debug"]
hybrid_debug = hybrid_result["debug"]

ai_titles_entered = len(hybrid_debug["title_candidates"]) - len(rule_debug["title_candidates"])
ai_highlights_entered = len(hybrid_debug["highlight_candidates"]) - len(rule_debug["highlight_candidates"])
top_ai_title, top_ai_title_score = find_top_extra_candidate(
    rule_debug["title_candidates"],
    hybrid_debug["title_candidates"],
    hybrid_debug["title_scores"],
)
top_ai_highlight, top_ai_highlight_score = find_top_extra_candidate(
    rule_debug["highlight_candidates"],
    hybrid_debug["highlight_candidates"],
    hybrid_debug["highlight_scores"],
)
final_changed = (
    rule_result["title"] != hybrid_result["title"]
    or rule_result["highlight"] != hybrid_result["highlight"]
)

print("=== INPUT ===")
print(RAW_TEXT)
print()

print("=== RULE RESULT ===")
print(f"TITLE: {rule_result['title']}")
print(f"HIGHLIGHT: {rule_result['highlight']}")
print(f"candidate_source={rule_debug['candidate_source']}")
print(f"fallback_used={str(rule_debug['fallback_used']).lower()}")
print()
print_candidates("TITLE CANDIDATES:", rule_debug["title_candidates"], rule_debug["title_scores"])
print_candidates("HIGHLIGHT CANDIDATES:", rule_debug["highlight_candidates"], rule_debug["highlight_scores"])

print("=== HYBRID RESULT ===")
print(f"TITLE: {hybrid_result['title']}")
print(f"HIGHLIGHT: {hybrid_result['highlight']}")
print(f"candidate_source={hybrid_debug['candidate_source']}")
print(f"fallback_used={str(hybrid_debug['fallback_used']).lower()}")
print()
print_candidates("TITLE CANDIDATES:", hybrid_debug["title_candidates"], hybrid_debug["title_scores"])
print_candidates("HIGHLIGHT CANDIDATES:", hybrid_debug["highlight_candidates"], hybrid_debug["highlight_scores"])

print("=== DIFF SUMMARY ===")
print(f"final_changed={str(final_changed).lower()}")
print(f"ai_titles_entered={ai_titles_entered}")
print(f"ai_highlights_entered={ai_highlights_entered}")
print(f"top_ai_title={shorten(top_ai_title) if top_ai_title else 'N/A'}")
print(f"top_ai_title_score={top_ai_title_score}")
print(f"top_ai_highlight={shorten(top_ai_highlight) if top_ai_highlight else 'N/A'}")
print(f"top_ai_highlight_score={top_ai_highlight_score}")
print(f"likely_reason={build_likely_reason(rule_result, hybrid_result)}")