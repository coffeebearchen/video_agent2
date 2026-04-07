# -*- coding: utf-8 -*-
"""
最小体验脚本：
1. 针对同一输入生成多种 style_mode 的 preview payload
2. 以控制台文本形式清晰展示风格差异
3. 不写文件，不接 UI，不改底层主链
"""

from pathlib import Path
import argparse
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.preview_formatter import format_style_previews
from modules.style_preview_service import DEFAULT_STYLE_MODES, build_style_previews


DEFAULT_CASES = [
    {
        "name": "CASE 1 FINANCE",
        "raw_text": "利率不是越低越好，关键要看降息发生时企业盈利和市场预期是否同步修复。",
        "content_mode": "finance",
        "style_modes": ["knowledge", "authority", "story"],
        "user_intent": None,
    },
    {
        "name": "CASE 2 PRODUCT",
        "raw_text": "这款协作工具把需求、排期和复盘放到同一界面，团队不用来回切系统，项目推进更快。",
        "content_mode": "product",
        "style_modes": ["knowledge", "authority", "story"],
        "user_intent": {
            "target_audience": "团队管理者",
            "emphasis": ["推进效率", "统一协作"],
        },
    },
    {
        "name": "CASE 3 ADS",
        "raw_text": "很多人以为防晒只是夏天要做，但真正拉开皮肤状态差距的，是一年四季的持续防护。",
        "content_mode": "ads",
        "style_modes": ["knowledge", "authority", "story"],
        "user_intent": {
            "desired_feel": "有转折感",
            "title_goal": "先打破误区再给出结论",
        },
    },
]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run multi-style preview comparisons.")
    parser.add_argument("--text", dest="raw_text", default="", help="Optional input text for a single custom preview run.")
    parser.add_argument("--content_mode", dest="content_mode", default="finance", help="Content mode for a single custom preview run.")
    parser.add_argument(
        "--styles",
        dest="styles",
        default=",".join(DEFAULT_STYLE_MODES),
        help="Comma-separated style modes for a single custom preview run.",
    )
    return parser.parse_args()


def _parse_style_modes(raw_styles: str) -> list[str]:
    style_modes: list[str] = []
    for item in str(raw_styles or "").split(","):
        normalized = item.strip().lower()
        if normalized and normalized not in style_modes:
            style_modes.append(normalized)
    return style_modes or DEFAULT_STYLE_MODES[:]


def _run_single_case(case_name: str, payload: dict) -> None:
    preview_results = build_style_previews(
        raw_text=payload["raw_text"],
        content_mode=payload["content_mode"],
        style_modes=payload["style_modes"],
        user_intent=payload.get("user_intent"),
    )
    print(f"\n#### {case_name} ####")
    print(f"content_mode: {payload['content_mode']}")
    print(f"raw_text: {payload['raw_text']}")
    print(format_style_previews(preview_results))
    print()


def main() -> None:
    args = _parse_args()

    if str(args.raw_text or "").strip():
        custom_case = {
            "raw_text": str(args.raw_text).strip(),
            "content_mode": str(args.content_mode or "finance").strip().lower() or "finance",
            "style_modes": _parse_style_modes(args.styles),
            "user_intent": None,
        }
        _run_single_case("CUSTOM CASE", custom_case)
        return

    for case in DEFAULT_CASES:
        _run_single_case(case["name"], case)


if __name__ == "__main__":
    main()