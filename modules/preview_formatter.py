# -*- coding: utf-8 -*-
"""
文件名：preview_formatter.py
作用说明：
1. 将多风格 preview 结果格式化为控制台可读文本
2. 只处理展示文本整理，不负责业务决策
3. 保持输出简单稳定，便于直接观察风格差异
"""


def _format_bullets(items: list[str]) -> list[str]:
    if not isinstance(items, list) or not items:
        return ["- (empty)"]

    lines: list[str] = []
    for item in items:
        lines.append(f"- {str(item or '').strip()}")
    return lines or ["- (empty)"]


def format_style_previews(preview_results: list[dict]) -> str:
    """将多风格 preview 结果整理成控制台可读文本。"""
    sections: list[str] = []

    for result in preview_results:
        style_mode = str(result.get("style_mode", "") or "unknown").strip()
        payload = result.get("payload", {}) if isinstance(result.get("payload"), dict) else {}
        meta = payload.get("meta", {}) if isinstance(payload.get("meta"), dict) else {}
        display = payload.get("display", {}) if isinstance(payload.get("display"), dict) else {}

        lines = [
            "=" * 30,
            f"STYLE: {style_mode}",
            "-" * 30,
            f"title: {payload.get('title', '')}",
            "highlight:",
            * _format_bullets(payload.get("highlight", [])),
            f"display.headline: {display.get('headline', '')}",
            "display.bullets:",
            * _format_bullets(display.get("bullets", [])),
            f"fallback_used: {bool(meta.get('fallback_used', False))}",
        ]
        sections.append("\n".join(lines))

    return "\n\n".join(sections)