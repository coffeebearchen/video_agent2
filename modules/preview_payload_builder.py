# -*- coding: utf-8 -*-
"""
文件名：preview_payload_builder.py
作用说明：
1. 将 AI 直出结果转换为统一 preview payload
2. 串接 ai_direct_generator 与 output_adapter
3. 不承担模型调用细节之外的业务扩展
"""

from modules.ai_direct_generator import generate_ai_direct
from modules.output_adapter import adapt_ai_output


def build_preview_payload(
    raw_text: str,
    content_mode: str,
    style_mode: str,
    user_intent: dict | None = None,
) -> dict:
    """生成统一可消费的 preview payload。"""
    generated_result = generate_ai_direct(
        raw_text=raw_text,
        content_mode=content_mode,
        style_mode=style_mode,
        user_intent=user_intent,
    )
    adapted_result = adapt_ai_output(generated_result)

    return {
        "title": adapted_result["title"],
        "highlight": adapted_result["highlight"],
        "display": {
            "headline": adapted_result["title"],
            "bullets": adapted_result["highlight"],
        },
        "meta": adapted_result["meta"],
    }