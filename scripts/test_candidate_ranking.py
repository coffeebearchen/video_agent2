from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.content_candidate import generate_candidates
from modules.content_ranking import rank_candidates


raw_text = (
    sys.argv[1]
    if len(sys.argv) > 1
    else "利率是资金的价格，资产价格会随着贴现率变化而波动，不是所有降息都会立刻推动股市上涨，而是取决于市场预期和盈利修复。"
)

candidates = generate_candidates(raw_text)
ranking = rank_candidates(candidates)

print("=== TITLE CANDIDATES ===")
for index, title in enumerate(candidates["title_candidates"]):
    print(f"[{index}] {title} (score: {ranking['title_scores'][index]})")

print()
print(f"BEST TITLE: {ranking['best_title']}")
print()
print("=== HIGHLIGHT CANDIDATES ===")
for index, highlight in enumerate(candidates["highlight_candidates"]):
    print(f"[{index}] {highlight} (score: {ranking['highlight_scores'][index]})")

print()
print(f"BEST HIGHLIGHT: {ranking['best_highlight']}")