from typing import Any, Dict

from modules.content_constraints import apply_content_constraints


def build_default_content_spec(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    ContentSpec + Constraint-A
    控制 Title / Highlight 内容来源
    并对内容做最小约束
    """
    default_title = "Default Title"
    default_highlight_zh = "默认高亮内容"
    default_highlight_en = "Default highlight"

    title_mode = "auto"
    highlight_mode = "auto"

    title_text = default_title
    highlight_zh = default_highlight_zh
    highlight_en = default_highlight_en

    if "title" in input_data and str(input_data["title"]).strip():
        title_mode = "manual_override"
        title_text = str(input_data["title"]).strip()

    if "highlight" in input_data and isinstance(input_data["highlight"], dict):
        raw_zh = str(input_data["highlight"].get("zh", "")).strip()
        raw_en = str(input_data["highlight"].get("en", "")).strip()

        if raw_zh or raw_en:
            highlight_mode = "manual_override"
            if raw_zh:
                highlight_zh = raw_zh
            if raw_en:
                highlight_en = raw_en

    constrained = apply_content_constraints(
        title_text=title_text,
        highlight_zh=highlight_zh,
        highlight_en=highlight_en,
    )

    return {
        "title": {
            "mode": title_mode,
            "text": constrained["title"],
        },
        "highlight": {
            "mode": highlight_mode,
            "zh": constrained["highlight_zh"],
            "en": constrained["highlight_en"],
        },
    }