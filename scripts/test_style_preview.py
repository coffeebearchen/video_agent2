from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.preview_renderer import generate_preview_frame


styles = [
    "creator_clean",
    "personal_ip",
    "product_focus",
    "life_story",
    "ai_control_lab",
]


print("=== STYLE TEST ===")

for style in styles:
    path = f"output/style_{style}.png"

    generate_preview_frame(
        style_name=style,
        output_path=path,
        pipeline_input={
            "title": "利率影响资产价格",
            "highlight": {
                "zh": "利率变化",
                "en": "Interest rate",
            },
        },
    )

    print(f"[OK] {style}")