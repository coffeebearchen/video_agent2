# -*- coding: utf-8 -*-
"""
最小产品入口：
1. 接收用户输入的原文内容
2. 对同一内容生成多种风格结果
3. 以更像产品而不是 debug 工具的方式输出标题与视频脚本
"""

from pathlib import Path
import json
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.demo_formatter import format_demo_results
from modules.output_adapter import adapt_ai_output
from modules.preview_enhancer import build_enhanced_preview
from modules.prompt_builder import build_prompt
from modules.llm_client import call_llm
from modules.style_prompt_enhancer import enhance_style_prompt


DEMO_STYLES = ["knowledge", "authority", "story"]
DEFAULT_INPUT_TEXT = "利率不是越低越好，关键要看降息发生时企业盈利和市场预期是否同步修复。"


def _compact_text(text: str) -> str:
    return "".join(ch for ch in str(text or "") if ch not in " \t\r\n，。！？；：,.!?;:\"'“”‘’（）()[]【】")


def _strip_code_fence(text: str) -> str:
    normalized = str(text or "").strip()
    if not normalized.startswith("```"):
        return normalized

    lines = normalized.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _extract_json_text(text: str) -> str:
    normalized = _strip_code_fence(text)
    start = normalized.find("{")
    end = normalized.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return ""
    return normalized[start:end + 1]


def _parse_demo_payload(raw_output: str) -> dict:
    normalized = str(raw_output or "").strip()
    if not normalized:
        return {}

    try:
        parsed = json.loads(normalized)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        pass

    json_text = _extract_json_text(normalized)
    if not json_text:
        return {}

    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError:
        return {}

    return parsed if isinstance(parsed, dict) else {}


def _normalize_demo_output_payload(payload: dict) -> dict:
    normalized = payload if isinstance(payload, dict) else {}
    title = normalized.get("title")
    highlight = normalized.get("highlight")

    if not highlight and normalized.get("highlights"):
        highlight = normalized.get("highlights")

    return {
        "title": title,
        "highlight": highlight,
    }


def _fallback_output(raw_text: str) -> dict:
    text = str(raw_text or "").strip() or "内容重点"
    title = text[:18].rstrip("，,。；;：:、 ") or "内容重点"
    parts = [item.strip() for item in text.replace("\r", "\n").replace("。", "\n").split("\n") if item.strip()]
    highlights = parts[:2] if parts else [title]
    return {
        "title": title,
        "highlight": highlights,
    }


def _split_raw_parts(raw_text: str) -> list[str]:
    text = str(raw_text or "").replace("\r", "\n")
    separators = ["。", "！", "？", "；", "\n", "，", ","]
    parts = [text]
    for separator in separators:
        next_parts: list[str] = []
        for part in parts:
            next_parts.extend(part.split(separator))
        parts = next_parts
    return [part.strip() for part in parts if part.strip()]


def _clean_fragment(text: str, max_length: int = 22) -> str:
    normalized = str(text or "").strip().rstrip("，,。；;：:、 ")
    if len(normalized) <= max_length:
        return normalized
    return normalized[:max_length].rstrip("，,。；;：:、 ")


def _dedupe_keep_order(items: list[str]) -> list[str]:
    results = []
    seen = set()
    for item in items:
        normalized = str(item or "").strip()
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        results.append(normalized)
    return results


def _extract_focus_subject(parts: list[str]) -> str:
    source = parts[0] if parts else "内容"
    for marker in ["不是", "要看", "关键", "本质", "真正", "但", "其实"]:
        if marker in source:
            candidate = source.split(marker, 1)[0].strip()
            if candidate:
                return _clean_fragment(candidate, max_length=8)
    return _clean_fragment(source, max_length=8) or "内容"


def _build_knowledge_safe_output(parts: list[str]) -> dict:
    first = _clean_fragment(parts[0] if parts else "内容重点", max_length=20) or "内容重点"
    second = _clean_fragment(parts[1] if len(parts) > 1 else first, max_length=22) or first
    third = _clean_fragment(parts[2] if len(parts) > 2 else second, max_length=22) or second

    title = f"本质上，关键在于{second}" if second else f"本质上，要看{first}"
    highlights = _dedupe_keep_order(
        [
            f"本质上，不是只看{first}。" if first else "本质上，要先看核心关系。",
            f"关键在于{second}。" if second else "关键在于核心条件是否成立。",
            f"不是停在表面变化，而是回到{third}。" if third else "不是停在表面变化，而是回到核心关系。",
        ]
    )
    return {
        "title": title.rstrip("，,。；;：:、 ") or "本质上，要看核心关系",
        "highlight": highlights[:3] or ["本质上，要看核心关系。"],
    }


def _build_authority_safe_output(parts: list[str]) -> dict:
    subject = _extract_focus_subject(parts)
    second = _clean_fragment(parts[1] if len(parts) > 1 else parts[0] if parts else "核心条件", max_length=22) or "核心条件"

    title = f"不要只看{subject}"
    highlights = _dedupe_keep_order(
        [
            f"不要只盯{subject}。",
            f"真正重要的是{second}。",
        ]
    )
    return {
        "title": title.rstrip("，,。；;：:、 ") or "不要只看表面",
        "highlight": highlights[:2] or ["真正重要的是核心条件。"],
    }


def _build_story_safe_output(parts: list[str]) -> dict:
    subject = _extract_focus_subject(parts)
    first = _clean_fragment(parts[0] if parts else subject, max_length=20) or subject
    second = _clean_fragment(parts[1] if len(parts) > 1 else first, max_length=22) or first

    title = f"很多人盯着{subject}，其实真正关键不在这里"
    highlights = _dedupe_keep_order(
        [
            f"很多人一上来就盯着{first}。",
            f"但真正关键的，不是{subject}本身。",
            f"而是{second}。",
        ]
    )
    return {
        "title": title.rstrip("，,。；;：:、 ") or "很多人先看表面，其实关键在后面",
        "highlight": highlights[:3] or ["很多人先看表面，但真正关键在后面。"],
    }


def _build_style_safe_output(raw_text: str, style_mode: str) -> dict:
    parts = _split_raw_parts(raw_text)

    style_key = str(style_mode or "").strip().lower()
    if style_key == "authority":
        return _build_authority_safe_output(parts)
    if style_key == "story":
        return _build_story_safe_output(parts)
    return _build_knowledge_safe_output(parts)


def _is_style_obvious(adapted_output: dict, style_mode: str) -> bool:
    title = str(adapted_output.get("title", "") or "")
    highlights = [str(item or "") for item in adapted_output.get("highlight", []) if str(item or "").strip()]
    combined = " ".join([title] + highlights)
    style_key = str(style_mode or "").strip().lower()

    if style_key == "authority":
        if len(highlights) < 1 or len(highlights) > 2:
            return False
        markers = ["不要只看", "关键是", "真正重要的是", "核心不是"]
        return any(marker in combined for marker in markers)

    if style_key == "story":
        if len(highlights) < 2 or len(highlights) > 3:
            return False
        story_markers = ["很多人", "但", "其实", "别只看", "你以为"]
        return any(marker in combined for marker in story_markers)

    if len(highlights) < 2 or len(highlights) > 3:
        return False
    knowledge_markers = ["本质上", "关键在于", "因为", "所以", "不是", "而是"]
    return any(marker in combined for marker in knowledge_markers)


def _is_grounded_output(adapted_output: dict, raw_text: str) -> bool:
    source = _compact_text(raw_text)
    if len(source) < 4:
        return True

    combined_output = _compact_text(adapted_output.get("title", ""))
    for item in adapted_output.get("highlight", []):
        combined_output += _compact_text(item)

    if not combined_output:
        return False

    for index in range(len(source) - 3):
        fragment = source[index:index + 4]
        if fragment and fragment in combined_output:
            return True
    return False


def _generate_demo_result(raw_text: str, content_mode: str, style_mode: str) -> dict:
    base_prompt_result = build_prompt(
        raw_text=raw_text,
        content_mode=content_mode,
        style_mode=style_mode,
        user_intent=None,
    )
    enhanced_prompt = enhance_style_prompt(style_mode, base_prompt_result["prompt"])

    try:
        raw_output = call_llm(enhanced_prompt)
        parsed_output = _normalize_demo_output_payload(_parse_demo_payload(raw_output))
    except Exception:
        parsed_output = {}

    adapted_output = adapt_ai_output(parsed_output)
    if not adapted_output["title"] or not adapted_output["highlight"]:
        adapted_output = adapt_ai_output(_build_style_safe_output(raw_text, style_mode))
    elif not _is_grounded_output(adapted_output, raw_text):
        adapted_output = adapt_ai_output(_build_style_safe_output(raw_text, style_mode))
    elif not _is_style_obvious(adapted_output, style_mode):
        adapted_output = adapt_ai_output(_build_style_safe_output(raw_text, style_mode))

    preview = build_enhanced_preview(
        title=adapted_output["title"],
        highlight=adapted_output["highlight"],
    )

    return {
        "style_mode": style_mode,
        "preview": preview,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(encoding="utf-8")

    print("请输入内容：")
    print("> ", end="", flush=True)
    user_input = input().strip()

    raw_text = user_input or DEFAULT_INPUT_TEXT
    content_mode = "finance"

    results = []
    for style_mode in DEMO_STYLES:
        results.append(_generate_demo_result(raw_text, content_mode, style_mode))

    print()
    print(format_demo_results(results))


if __name__ == "__main__":
    main()