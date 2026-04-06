from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.preview_renderer import generate_preview_frame


titles = [
    "利率下降会如何影响资产价格走势",
    "为什么贴现率变化会改变估值模型",
    "通胀预期如何传导到利率市场",
    "资金成本上升对企业利润的影响",
    "降息为什么不一定立刻利好股市",
    "美债收益率变化如何影响全球资产",
    "资产价格为什么会对利率如此敏感",
    "信用扩张如何推动风险资产上涨",
    "市场为什么总在流动性拐点重估资产",
    "汇率变化如何影响出口企业利润",
]


print("=== TITLE REGRESSION TEST ===")

for i, title in enumerate(titles, start=1):
    path = f"output/title_test_{i}.png"

    generate_preview_frame(
        style_name="creator_clean",
        output_path=path,
        pipeline_input={
            "title": title,
            "highlight": {
                "zh": "利率变化",
                "en": "Interest rate",
            },
        },
    )

    print(f"[OK] {i}: {title}")