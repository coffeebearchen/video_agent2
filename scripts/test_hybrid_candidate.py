from pathlib import Path
import json
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.content_candidate_hybrid import generate_hybrid_candidates
from modules.content_candidate_deepseek import diagnose_ai_candidates, get_deepseek_runtime_status
from modules.content_ranking import rank_candidates


CONFIG_PATH = PROJECT_ROOT / "config.json"


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


raw_text = (
    sys.argv[1]
    if len(sys.argv) > 1
    else "利率是资金的价格，资产价格会随着贴现率变化，不是所有降息都会立刻推动股市上涨，而是取决于市场预期。"
)

base_config = load_config()
rule_config = dict(base_config)
rule_config["ai_candidate"] = {
    "enabled": False,
    "provider": "deepseek",
    "timeout": base_config.get("ai_candidate", {}).get("timeout", 5),
}

hybrid_config = dict(base_config)

runtime_status = get_deepseek_runtime_status()
ai_result = diagnose_ai_candidates(raw_text)

rule_only = generate_hybrid_candidates(raw_text, rule_config)
hybrid = generate_hybrid_candidates(raw_text, hybrid_config)
rule_ranked = rank_candidates(rule_only)
hybrid_ranked = rank_candidates(hybrid)
fallback_used = not ai_result.get("ok")

print("=== CONFIG STATUS ===")
print(f"provider={runtime_status['provider']}")
print(f"provider_source={runtime_status['provider_source']}")
print(f"base_url={runtime_status['base_url']}")
print(f"base_url_source={runtime_status['base_url_source']}")
print(f"api_key_present={str(runtime_status['api_key_present']).lower()}")
print(f"api_key_source={runtime_status['api_key_source']}")
print(f"timeout={runtime_status['timeout']}")
print(f"timeout_source={runtime_status['timeout_source']}")
print(f"ai_enabled={str(hybrid_config.get('ai_candidate', {}).get('enabled', False)).lower()}")
print()

print("=== AI RESULT ===")
if ai_result.get("ok"):
    ai_candidates = ai_result.get("candidates", {})
    print("status=success")
    print(f"stage={ai_result['stage']}")
    print(f"message={ai_result['message']}")
    print(f"title_count={len(ai_candidates.get('title_candidates', []))}")
    print(f"highlight_count={len(ai_candidates.get('highlight_candidates', []))}")
    print(f"titles={ai_candidates.get('title_candidates', [])}")
    print(f"highlights={ai_candidates.get('highlight_candidates', [])}")
else:
    print("status=failed")
    print(f"stage={ai_result['stage']}")
    print(f"message={ai_result['message']}")
    print(f"request_sent={str(ai_result.get('request_sent', False)).lower()}")
    print(f"status_code={ai_result.get('status_code')}")
    print(f"response_preview={ai_result.get('response_preview', '')}")
print()

print("=== RULE ONLY ===")
print(f"title_count={len(rule_only['title_candidates'])}")
print(f"highlight_count={len(rule_only['highlight_candidates'])}")
print(f"best_title={rule_ranked['best_title']}")
print(f"best_highlight={rule_ranked['best_highlight']}")
print("title_candidates:")
for item in rule_only["title_candidates"]:
    print(f"- {item}")
print("highlight_candidates:")
for item in rule_only["highlight_candidates"]:
    print(f"- {item}")

print()
print("=== HYBRID RESULT ===")
print(f"title_count={len(hybrid['title_candidates'])}")
print(f"highlight_count={len(hybrid['highlight_candidates'])}")
print(f"best_title={hybrid_ranked['best_title']}")
print(f"best_highlight={hybrid_ranked['best_highlight']}")
print(f"fallback_used={str(fallback_used).lower()}")
print("title_candidates:")
for item in hybrid["title_candidates"]:
    print(f"- {item}")
print("highlight_candidates:")
for item in hybrid["highlight_candidates"]:
    print(f"- {item}")