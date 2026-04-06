# ContentSpec-B：真实 pipeline 输入适配器（只读最小版）

from typing import Any, Dict, Optional


def _safe_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def extract_title_from_pipeline_input(pipeline_input: Optional[Dict[str, Any]]) -> str:
    """
    从真实输入中提取最小 title 候选
    优先级：
    1. pipeline_input["title"]
    2. pipeline_input["content"]（截断）
    3. 空字符串
    """
    if not pipeline_input:
        return ""

    title = _safe_str(pipeline_input.get("title"))
    if title:
        return title

    content = _safe_str(pipeline_input.get("content"))
    if content:
        return content[:40]

    return ""


def extract_highlight_from_pipeline_input(pipeline_input: Optional[Dict[str, Any]]) -> Dict[str, str]:
    """
    从真实输入中提取最小 highlight 候选
    当前只做最保守的只读映射：
    1. pipeline_input["highlight"]["zh"/"en"]
    2. pipeline_input["content"] 作为 zh
    3. en 为空时给默认英文
    """
    empty_result = {"zh": "", "en": ""}

    if not pipeline_input:
        return empty_result

    raw_highlight = pipeline_input.get("highlight")
    if isinstance(raw_highlight, dict):
        zh = _safe_str(raw_highlight.get("zh"))
        en = _safe_str(raw_highlight.get("en"))
        if zh or en:
            return {
                "zh": zh,
                "en": en or "Default highlight",
            }

    content = _safe_str(pipeline_input.get("content"))
    if content:
        return {
            "zh": content[:28],
            "en": "Default highlight",
        }

    return empty_result


def build_content_input_from_pipeline(pipeline_input: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    统一输出给 ContentSpec 的 input_data 结构
    """
    title = extract_title_from_pipeline_input(pipeline_input)
    highlight = extract_highlight_from_pipeline_input(pipeline_input)

    result: Dict[str, Any] = {}

    if title:
        result["title"] = title

    if highlight.get("zh") or highlight.get("en"):
        result["highlight"] = highlight

    return result