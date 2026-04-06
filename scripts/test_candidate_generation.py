from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.content_candidate import generate_candidates


sample_text = (
    sys.argv[1]
    if len(sys.argv) > 1
    else "利率是资金的价格，资产价格会随着贴现率变化而波动，不是所有降息都会立刻推动股市上涨，而是取决于市场预期和盈利修复。"
)

result = generate_candidates(sample_text)

print("=== CANDIDATE GENERATION TEST ===")
print("raw_text:")
print(sample_text)
print()
print("title_candidates:")
for item in result["title_candidates"]:
    print(f"- {item}")
print()
print("highlight_candidates:")
for item in result["highlight_candidates"]:
    print(f"- {item}")