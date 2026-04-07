# -*- coding: utf-8 -*-
"""
结构化反馈映射层。

职责：
1. 解析反馈文本，映射为结构化控制变量
2. 标准化约束结构，确保 builder 侧字段稳定
3. 将结构化约束渲染为 prompt 可用的反馈约束块
"""

from __future__ import annotations


RULES = {
    "tone": {
        "less_academic": ["不要这么学术", "太学术", "更口语", "像人说话"],
        "more_story": ["像讲故事", "更故事化"],
        "more_casual": ["轻松一点", "别太严肃"],
    },
    "opening_style": {
        "more_hooked": ["开头更有冲击力", "开头抓人", "更吸引人"],
        "direct": ["直接一点", "别绕"],
        "soft": ["柔和一点", "开头柔一点"],
    },
    "title_style": {
        "short": ["标题短一点", "标题太长"],
        "punchy": ["标题更有力", "标题更炸"],
        "neutral": ["标题自然一点", "标题别太冲"],
    },
    "structure": {
        "tighter": ["收一点", "更紧凑"],
        "looser": ["展开一点", "更松一点"],
    },
    "highlight_density": {
        "lighter": ["重点少一点", "别太多重点"],
        "denser": ["多一点重点", "更突出重点"],
    },
    "keyword_density": {
        "richer": ["关键词多一点", "更丰富"],
        "focused": ["关键词聚焦一点"],
    },
}


MAPPING_TO_PROMPT = {
    "tone": {
        "less_academic": "Use less academic tone",
        "more_story": "Use storytelling style",
        "more_casual": "Use casual tone",
    },
    "opening_style": {
        "more_hooked": "Make opening more engaging",
        "direct": "Start more directly",
        "soft": "Use a softer opening",
    },
    "title_style": {
        "short": "Keep title concise",
        "punchy": "Make title more impactful",
        "neutral": "Keep title more neutral",
    },
    "structure": {
        "tighter": "Make structure tighter",
        "looser": "Allow more expansion",
    },
    "highlight_density": {
        "lighter": "Reduce highlight density",
        "denser": "Increase highlight emphasis",
    },
    "keyword_density": {
        "richer": "Enrich keywords",
        "focused": "Keep keywords focused",
    },
}


DEFAULT_CONSTRAINTS = {
    "tone": None,
    "opening_style": None,
    "title_style": None,
    "structure": None,
    "highlight_density": None,
    "keyword_density": None,
    "raw_feedback": None,
    "future_slots": {},
}


def normalize_feedback_constraints(constraints: dict | None) -> dict:
    normalized = dict(DEFAULT_CONSTRAINTS)
    if isinstance(constraints, dict):
        for key in DEFAULT_CONSTRAINTS:
            if key == "future_slots":
                continue
            normalized[key] = constraints.get(key)

        future_slots = constraints.get("future_slots")
        normalized["future_slots"] = future_slots if isinstance(future_slots, dict) else {}

    return normalized


def map_feedback(feedback_text: str) -> dict:
    normalized_text = str(feedback_text or "").strip()
    constraints = normalize_feedback_constraints({})

    if not normalized_text:
        return constraints

    for field, options in RULES.items():
        for option, phrases in options.items():
            for phrase in phrases:
                if phrase in normalized_text:
                    constraints[field] = option
                    break
            if constraints[field] is not None:
                break

    if not any(constraints[field] for field in RULES):
        constraints["raw_feedback"] = normalized_text

    return normalize_feedback_constraints(constraints)


def render_feedback_constraints(constraints: dict) -> str:
    normalized = normalize_feedback_constraints(constraints)
    if not any(normalized[field] for field in RULES) and not normalized.get("raw_feedback"):
        return ""

    lines = ["[Feedback Constraints]"]

    for field, options in MAPPING_TO_PROMPT.items():
        selected_option = normalized.get(field)
        if selected_option and selected_option in options:
            lines.append(f"- {options[selected_option]}")

    if normalized.get("raw_feedback"):
        lines.append(f"- User feedback: {normalized['raw_feedback']}")

    return "\n".join(lines)