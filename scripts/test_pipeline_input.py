from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.preview_renderer import generate_preview_frame


print("=== PIPELINE INPUT TEST ===")

generate_preview_frame(
    style_name="creator_clean",
    output_path="output/pipeline_test.png",
    pipeline_input={
        "content": "利率是资金的价格资产价格会随贴现率变化",
    },
)