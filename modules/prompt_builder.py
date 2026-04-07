# -*- coding: utf-8 -*-
"""
文件名：prompt_builder.py
作用说明：
1. 作为 prompt 合成层的唯一出口
2. 负责整合系统规则、内容模板、风格模板、用户补充偏好与原文
3. 不调用模型，不承担测试逻辑，不介入视频生成流程
"""

from typing import Any

from modules.prompt_rules import get_system_rules_text
from modules.prompt_templates import (
    DEFAULT_CONTENT_MODE,
    DEFAULT_STYLE_MODE,
    get_content_template,
    get_style_template,
)


def _normalize_mode(value: str | None, default_value: str) -> str:
    normalized = str(value or "").strip().lower()
    return normalized or default_value


def _normalize_raw_text(raw_text: str) -> str:
    text = str(raw_text or "").strip()
    return text or "未提供原始内容。"


def _stringify_user_value(value: Any) -> str:
    if isinstance(value, dict):
        parts: list[str] = []
        for sub_key, sub_value in value.items():
            sub_text = _stringify_user_value(sub_value)
            if sub_text:
                parts.append(f"{sub_key}={sub_text}")
        return "；".join(parts)

    if isinstance(value, (list, tuple, set)):
        parts = [str(item).strip() for item in value if str(item).strip()]
        return "、".join(parts)

    text = str(value or "").strip()
    return text


def _normalize_user_intent(user_intent: dict | None) -> dict[str, str]:
    if not isinstance(user_intent, dict):
        return {}

    normalized: dict[str, str] = {}
    for key, value in user_intent.items():
        clean_key = str(key or "").strip()
        clean_value = _stringify_user_value(value)
        if clean_key and clean_value:
            normalized[clean_key] = clean_value
    return normalized


def _build_user_intent_section(user_intent: dict[str, str]) -> str:
    if not user_intent:
        return "[用户补充偏好]\n- 未提供，当前按自动模式处理。"

    lines = [
        "[用户补充偏好]",
        "- 以下内容仅作补充，不得覆盖系统硬规则。",
    ]
    for key, value in user_intent.items():
        lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def _build_task_section() -> str:
    return "\n".join(
        [
            "[生成任务]",
            "请严格基于原文完成以下输出：",
            "1. 生成 1 个适合视频封面或上屏主标题的 title。",
            "2. 生成 2 到 3 个可直接上屏的 highlight。",
            "3. 生成 1 段后续可供视频文案主链继续使用的 prompt_summary。",
            "4. 不要编造原文之外的信息。",
            "5. 只输出 JSON，不要输出额外说明。",
            "6. 输出结构固定为：",
            '{"title":"...","highlights":["...","..."],"prompt_summary":"..."}',
        ]
    )


def build_prompt(
    raw_text: str,
    content_mode: str,
    style_mode: str,
    user_intent: dict | None = None,
) -> dict:
    """合成统一结构的最终 prompt。"""
    normalized_content_mode = _normalize_mode(content_mode, DEFAULT_CONTENT_MODE)
    normalized_style_mode = _normalize_mode(style_mode, DEFAULT_STYLE_MODE)
    normalized_raw_text = _normalize_raw_text(raw_text)
    normalized_user_intent = _normalize_user_intent(user_intent)

    prompt_sections = [
        "[系统硬规则]",
        get_system_rules_text(),
        "",
        "[内容模板]",
        get_content_template(normalized_content_mode),
        "",
        "[风格模板]",
        get_style_template(normalized_style_mode),
        "",
        _build_user_intent_section(normalized_user_intent),
        "",
        "[原始内容]",
        normalized_raw_text,
        "",
        _build_task_section(),
    ]

    final_prompt = "\n".join(prompt_sections).strip()

    return {
        "prompt": final_prompt,
        "meta": {
            "content_mode": normalized_content_mode,
            "style_mode": normalized_style_mode,
            "auto_mode": not bool(normalized_user_intent),
            "user_intent_used": bool(normalized_user_intent),
        },
    }