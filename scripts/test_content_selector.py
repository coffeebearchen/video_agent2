from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.content_selector import select_best_content


raw_text = (
    sys.argv[1]
    if len(sys.argv) > 1
    else "利率是资金的价格，资产价格会随着贴现率变化而波动，不是所有降息都会立刻推动股市上涨，而是取决于市场预期和盈利修复。"
)

result = select_best_content(raw_text)
debug = result["debug"]

print("=== FINAL OUTPUT ===")
print(f"TITLE: {result['title']}")
print(f"HIGHLIGHT: {result['highlight']}")
print()
print("=== DEBUG ===")
print("TITLE CANDIDATES:")
for index, title in enumerate(debug["title_candidates"]):
    print(f"[{index}] {title} (score: {debug['title_scores'][index]})")
print()
print("HIGHLIGHT CANDIDATES:")
for index, highlight in enumerate(debug["highlight_candidates"]):
    print(f"[{index}] {highlight} (score: {debug['highlight_scores'][index]})")