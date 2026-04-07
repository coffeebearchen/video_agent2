# -*- coding: utf-8 -*-
"""
文件名：output_adapter.py
作用说明：
1. 对 AI 直出结果做极薄结构清洗
2. 输出稳定的标准结构，供 preview 与后续使用层消费
3. 不负责模型调用、prompt 拼装和视频逻辑
"""

from typing import Any


def _normalize_text(value: Any) -> str:
    return str(value or "").strip()


def _normalize_highlight(value: Any) -> list[str]:
    if isinstance(value, list):
        items = value
    elif isinstance(value, str):
        items = [value]
    elif value is None:
        items = []
    else:
        items = [str(value)]

    results: list[str] = []
    for item in items:
        cleaned = _normalize_text(item)
        if cleaned:
            results.append(cleaned)
    return results


def adapt_ai_output(result: dict) -> dict:
    """将 AI 直出结果整理成稳定标准结构。"""
    source = result if isinstance(result, dict) else {}
    title = _normalize_text(source.get("title"))
    highlight = _normalize_highlight(source.get("highlight"))
    meta = source.get("meta") if isinstance(source.get("meta"), dict) else {}

    return {
        "title": title,
        "highlight": highlight,
        "meta": meta,
    }