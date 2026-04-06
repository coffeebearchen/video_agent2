from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.preview_renderer import generate_preview_frame


cases = [
    "利率是资金的价格资产价格会随贴现率变化",
    "这是一个非常长的高亮句子应该被截断",
    "短语测试",
]


print("=== HIGHLIGHT TEST ===")

for i, text in enumerate(cases, start=1):
    path = f"output/highlight_test_{i}.png"

    generate_preview_frame(
        style_name="creator_clean",
        output_path=path,
        pipeline_input={
            "title": "测试标题",
            "highlight": {
                "zh": text,
                "en": "This is a very long highlight sentence for testing",
            },
        },
    )

    print(f"[OK] {i}")