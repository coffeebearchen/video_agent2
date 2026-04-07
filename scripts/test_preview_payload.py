# -*- coding: utf-8 -*-
"""
最小测试脚本：
1. 验证 preview_payload_builder 是否能串接 AI 直出结果
2. 覆盖自动模式与半自动模式
3. 只输出控制台结果，不写入任何文件
"""

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.preview_payload_builder import build_preview_payload


def run_case(case_name: str, payload: dict) -> None:
    result = build_preview_payload(
        raw_text=payload["raw_text"],
        content_mode=payload["content_mode"],
        style_mode=payload["style_mode"],
        user_intent=payload.get("user_intent"),
    )

    print(f"===== {case_name} =====")
    print("meta:")
    print(result["meta"])
    print("title:")
    print(result["title"])
    print("highlight:")
    print(result["highlight"])
    print("display:")
    print(result["display"])
    print()


def main() -> None:
    cases = [
        {
            "name": "CASE 1 AUTO FINANCE KNOWLEDGE",
            "raw_text": "利率不是越低越好，关键要看降息发生时企业盈利和市场预期是否同步修复。",
            "content_mode": "finance",
            "style_mode": "knowledge",
        },
        {
            "name": "CASE 2 SEMI PRODUCT AUTHORITY",
            "raw_text": "这款协作工具把需求、排期和复盘放到同一界面，团队不用来回切系统，项目推进更快。",
            "content_mode": "product",
            "style_mode": "authority",
            "user_intent": {
                "target_audience": "团队管理者",
                "emphasis": ["推进效率", "统一协作"],
            },
        },
        {
            "name": "CASE 3 SEMI ADS STORY",
            "raw_text": "很多人以为防晒只是夏天要做，但真正拉开皮肤状态差距的，是一年四季的持续防护。",
            "content_mode": "ads",
            "style_mode": "story",
            "user_intent": {
                "desired_feel": "有转折感",
                "title_goal": "先打破误区再给出结论",
            },
        },
    ]

    for case in cases:
        run_case(case["name"], case)


if __name__ == "__main__":
    main()