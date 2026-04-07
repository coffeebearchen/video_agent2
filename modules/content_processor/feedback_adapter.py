# -*- coding: utf-8 -*-
"""
带反馈 regenerate 的最小反馈适配层。

职责：
1. 解析用户 feedback_text 中的常见轻反馈信号
2. 生成 prompt 可用的反馈约束块
3. 在 fallback / 兜底场景中提供轻量表达调整
"""

from __future__ import annotations


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _remove_prefix(text: str, prefix: str) -> str:
    if text.startswith(prefix):
        return text[len(prefix):]
    return text


def _coerce_feedback_preferences(feedback_preferences: dict | None) -> dict:
    source = feedback_preferences if isinstance(feedback_preferences, dict) else {}

    if "has_feedback" in source or "title_length" in source or "tightness" in source:
        return {
            "raw_text": str(source.get("raw_text") or source.get("raw_feedback") or "").strip(),
            "has_feedback": bool(source.get("has_feedback") or source.get("raw_text") or source.get("raw_feedback")),
            "matched_rules": list(source.get("matched_rules") or []),
            "title_length": source.get("title_length"),
            "tone": source.get("tone"),
            "opening_style": source.get("opening_style"),
            "tightness": source.get("tightness"),
            "keyword_density": source.get("keyword_density"),
            "highlight_density": source.get("highlight_density"),
        }

    raw_feedback = str(source.get("raw_feedback") or "").strip()
    has_structured_feedback = any(
        source.get(field)
        for field in [
            "tone",
            "opening_style",
            "title_style",
            "structure",
            "highlight_density",
            "keyword_density",
        ]
    )
    normalized = {
        "raw_text": raw_feedback,
        "has_feedback": bool(raw_feedback) or has_structured_feedback,
        "matched_rules": [],
        "title_length": None,
        "tone": source.get("tone"),
        "opening_style": source.get("opening_style"),
        "tightness": source.get("structure"),
        "keyword_density": source.get("keyword_density"),
        "highlight_density": source.get("highlight_density"),
    }

    title_style = source.get("title_style")
    if title_style == "short":
        normalized["title_length"] = "short"
        normalized["matched_rules"].append("title_shorter")
    elif title_style == "punchy":
        normalized["matched_rules"].append("title_punchy")

    if normalized["tone"]:
        normalized["matched_rules"].append(f"tone_{normalized['tone']}")
    if normalized["opening_style"]:
        normalized["matched_rules"].append(f"opening_{normalized['opening_style']}")
    if normalized["tightness"]:
        normalized["matched_rules"].append(f"structure_{normalized['tightness']}")
    if normalized["keyword_density"]:
        normalized["matched_rules"].append(f"keywords_{normalized['keyword_density']}")
    if normalized["highlight_density"]:
        normalized["matched_rules"].append(f"highlights_{normalized['highlight_density']}")

    return normalized


def parse_feedback_preferences(feedback_text: str) -> dict:
    normalized_text = str(feedback_text or "").strip()
    compact_text = normalized_text.replace(" ", "")
    preferences = {
        "raw_text": normalized_text,
        "has_feedback": bool(normalized_text),
        "matched_rules": [],
        "title_length": None,
        "tone": None,
        "opening_style": None,
        "tightness": None,
        "keyword_density": None,
        "highlight_density": None,
    }

    if not normalized_text:
        return preferences

    if _contains_any(compact_text, ["标题短一点", "标题再短一点", "标题短一些", "题目短一点"]):
        preferences["title_length"] = "short"
        preferences["matched_rules"].append("title_shorter")

    if _contains_any(compact_text, ["不要这么学术", "别太学术", "更口语一点", "更像人说话", "少一点学术"]):
        preferences["tone"] = "less_academic"
        preferences["matched_rules"].append("tone_less_academic")

    if _contains_any(compact_text, ["更像讲故事", "更有带入感", "开头更有带入感", "更有冲击力", "开头抓人一点", "更抓人"]):
        preferences["opening_style"] = "more_hooked"
        if preferences["tone"] is None:
            preferences["tone"] = "more_storylike"
        preferences["matched_rules"].append("opening_more_hooked")

    if _contains_any(compact_text, ["收一点", "别太满", "更克制一点", "收一些"]):
        preferences["tightness"] = "tighter"
        preferences["matched_rules"].append("tightness_tighter")

    if _contains_any(compact_text, ["再活一点", "更展开一点", "再放一点", "更丰富一点"]):
        preferences["tightness"] = "looser"
        preferences["matched_rules"].append("tightness_looser")

    if _contains_any(compact_text, ["关键词多一点", "关键词再丰富一点", "关键词丰富一点", "关键词更多"]):
        preferences["keyword_density"] = "richer"
        preferences["matched_rules"].append("keywords_richer")

    if _contains_any(compact_text, ["重点少一点", "高亮少一点"]):
        preferences["highlight_density"] = "lighter"
        preferences["matched_rules"].append("highlights_lighter")

    if _contains_any(compact_text, ["重点更清楚一点", "高亮更清楚一点", "重点清楚一点"]):
        preferences["highlight_density"] = "clearer"
        preferences["matched_rules"].append("highlights_clearer")

    if _contains_any(compact_text, ["高亮再多一点", "重点再多一点", "高亮多一点"]):
        preferences["highlight_density"] = "denser"
        preferences["matched_rules"].append("highlights_denser")

    return preferences


def build_feedback_constraint_section(feedback_preferences: dict) -> str:
    if not feedback_preferences.get("has_feedback"):
        return ""

    lines = [
        "[Feedback Constraints]",
        "当前为带反馈 regenerate。",
        "保持主题、content_mode、style_mode、reference media、主参数不变。",
        "只允许调整标题长度、开头句式、语气、highlights 密度、keywords 丰富度、表达松紧度。",
    ]

    if feedback_preferences.get("title_length") == "short":
        lines.append("- Make title shorter and tighter.")

    if feedback_preferences.get("tone") == "less_academic":
        lines.append("- Use less academic tone and more natural spoken wording.")
    elif feedback_preferences.get("tone") == "more_storylike":
        lines.append("- Make the tone feel more storylike and easier to follow.")

    if feedback_preferences.get("opening_style") == "more_hooked":
        lines.append("- Make the opening line more engaging and more hooked.")

    if feedback_preferences.get("tightness") == "tighter":
        lines.append("- Tighten the expression and avoid being too full or too dense.")
    elif feedback_preferences.get("tightness") == "looser":
        lines.append("- Loosen the expression slightly and allow a bit more expansion.")

    if feedback_preferences.get("keyword_density") == "richer":
        lines.append("- Enrich keywords while keeping them tied to the same topic.")

    if feedback_preferences.get("highlight_density") == "lighter":
        lines.append("- Make highlights fewer and lighter.")
    elif feedback_preferences.get("highlight_density") == "clearer":
        lines.append("- Make highlights clearer and easier to scan.")
    elif feedback_preferences.get("highlight_density") == "denser":
        lines.append("- Make highlights denser, but do not change the topic.")

    if not feedback_preferences.get("matched_rules"):
        lines.append(f"- User feedback: {feedback_preferences.get('raw_text', '')}")
    else:
        lines.append(f"- Raw user feedback: {feedback_preferences.get('raw_text', '')}")

    return "\n".join(lines)


def apply_feedback_preferences(content_package: dict, feedback_preferences: dict, style_mode: str) -> dict:
    feedback_preferences = _coerce_feedback_preferences(feedback_preferences)

    if not feedback_preferences.get("has_feedback"):
        return content_package

    title = str(content_package.get("title", "") or "").strip()
    script = [str(item or "").strip() for item in content_package.get("script", []) if str(item or "").strip()]
    highlights = [str(item or "").strip() for item in content_package.get("highlights", []) if str(item or "").strip()]
    keywords = [str(item or "").strip() for item in content_package.get("keywords", []) if str(item or "").strip()]
    style_key = str(style_mode or "").strip().lower()

    if feedback_preferences.get("title_length") == "short" and title:
        title = title[:14].rstrip("，,。；;：:、 ")

    if feedback_preferences.get("tone") == "less_academic":
        replacements = {
            "本质上": "说白了",
            "关键在于": "关键是",
            "并非": "不是",
        }
        for source, target in replacements.items():
            title = title.replace(source, target)
            script = [item.replace(source, target) for item in script]
            highlights = [item.replace(source, target) for item in highlights]
    elif feedback_preferences.get("tone") == "more_story":
        if script and "很多人" not in script[0]:
            script[0] = f"很多人一开始都会忽略这一层，{script[0]}"
    elif feedback_preferences.get("tone") == "more_casual":
        replacements = {
            "本质上": "其实",
            "关键在于": "关键是",
            "真正重要的是": "更重要的是",
        }
        for source, target in replacements.items():
            title = title.replace(source, target)
            script = [item.replace(source, target) for item in script]

    if feedback_preferences.get("opening_style") == "more_hooked" and script:
        first_line = script[0]
        if style_key == "story":
            if "很多人" not in first_line:
                script[0] = f"很多人一上来就会这么看，{first_line}"
        else:
            if "先别急着下结论" not in first_line:
                script[0] = f"先别急着下结论，{first_line}"
    elif feedback_preferences.get("opening_style") == "direct" and script:
        script[0] = _remove_prefix(script[0], "很多人一上来就会这么看，")
        script[0] = _remove_prefix(script[0], "先别急着下结论，")
    elif feedback_preferences.get("opening_style") == "soft" and script:
        if not script[0].startswith("可以先看一个简单判断，"):
            script[0] = f"可以先看一个简单判断，{script[0]}"

    if feedback_preferences.get("tightness") == "tighter":
        title = title[:16].rstrip("，,。；;：:、 ")
        script = [item[:28].rstrip("，,。；;：:、 ") + ("。" if item and not item.endswith("。") else "") for item in script[:3]]
    elif feedback_preferences.get("tightness") == "looser" and script:
        script[0] = script[0].rstrip("。") + "，把这层关系先带出来。"

    if source_title_style := feedback_preferences.get("title_length"):
        if source_title_style == "short" and title:
            title = title[:14].rstrip("，,。；;：:、 ")

    if "title_punchy" in feedback_preferences.get("matched_rules", []) and title:
        if not title.endswith("？") and not title.endswith("!") and not title.endswith("！"):
            title = title.rstrip("，,。；;：:、 ") + "？"

    if feedback_preferences.get("highlight_density") == "lighter":
        highlights = highlights[:2]
    elif feedback_preferences.get("highlight_density") == "clearer":
        highlights = [item[:14].rstrip("，,。；;：:、 ") for item in highlights[:3]]
    elif feedback_preferences.get("highlight_density") == "denser" and len(highlights) < 3:
        for item in script:
            candidate = item[:14].rstrip("，,。；;：:、 ")
            if candidate and candidate not in highlights:
                highlights.append(candidate)
            if len(highlights) >= 3:
                break

    if feedback_preferences.get("keyword_density") == "richer":
        extra_keywords = ["反馈调整", "二次生成"]
        if feedback_preferences.get("tone") == "less_academic":
            extra_keywords.append("口语化")
        if feedback_preferences.get("opening_style") == "more_hooked":
            extra_keywords.append("开头抓人")
        for item in extra_keywords:
            if item not in keywords:
                keywords.append(item)

    cleaned_script = []
    for item in script[:3]:
        text = item.strip()
        if not text:
            continue
        if text[-1] not in "。！？!?":
            text = f"{text}。"
        cleaned_script.append(text)

    cleaned_highlights = []
    for item in highlights[:3]:
        text = item.strip().rstrip("，,。；;：:、 ")
        if text and text not in cleaned_highlights:
            cleaned_highlights.append(text)

    cleaned_keywords = []
    for item in keywords[:6]:
        text = item.strip().rstrip("，,。；;：:、 ")
        if text and text not in cleaned_keywords:
            cleaned_keywords.append(text)

    return {
        **content_package,
        "title": title or content_package.get("title", ""),
        "script": cleaned_script or content_package.get("script", []),
        "highlights": cleaned_highlights or content_package.get("highlights", []),
        "keywords": cleaned_keywords or content_package.get("keywords", []),
    }