from pathlib import Path
import json
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.content_selector import select_best_content


CONFIG_PATH = PROJECT_ROOT / "config.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


raw_text = (
    sys.argv[1]
    if len(sys.argv) > 1
    else "利率是资金的价格，资产价格会随着贴现率变化而波动，不是所有降息都会立刻推动股市上涨，而是取决于市场预期和盈利修复。"
)

base_config = load_config()
rule_config = dict(base_config)
rule_config["hybrid_selector"] = {"enabled": False}

rule_result = select_best_content(raw_text, config=rule_config)
rule_debug = rule_result["debug"]

hybrid_result = select_best_content(raw_text, config=base_config)
hybrid_debug = hybrid_result["debug"]

print("=== RULE ONLY ===")
print(f"TITLE: {rule_result['title']}")
print(f"HIGHLIGHT: {rule_result['highlight']}")
print(f"candidate_source={rule_debug['candidate_source']}")
print(f"fallback_used={str(rule_debug['fallback_used']).lower()}")
print()
print("TITLE CANDIDATES:")
for index, title in enumerate(rule_debug["title_candidates"]):
    print(f"[{index}] {title} (score: {rule_debug['title_scores'][index]})")
print()
print("HIGHLIGHT CANDIDATES:")
for index, highlight in enumerate(rule_debug["highlight_candidates"]):
    print(f"[{index}] {highlight} (score: {rule_debug['highlight_scores'][index]})")
print()

print("=== HYBRID ===")
print(f"TITLE: {hybrid_result['title']}")
print(f"HIGHLIGHT: {hybrid_result['highlight']}")
print(f"candidate_source={hybrid_debug['candidate_source']}")
print(f"fallback_used={str(hybrid_debug['fallback_used']).lower()}")
print()
print("TITLE CANDIDATES:")
for index, title in enumerate(hybrid_debug["title_candidates"]):
    print(f"[{index}] {title} (score: {hybrid_debug['title_scores'][index]})")
print()
print("HIGHLIGHT CANDIDATES:")
for index, highlight in enumerate(hybrid_debug["highlight_candidates"]):
    print(f"[{index}] {highlight} (score: {hybrid_debug['highlight_scores'][index]})")