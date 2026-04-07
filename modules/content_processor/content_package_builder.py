# -*- coding: utf-8 -*-
"""
正式 content package 生成层。

职责：
1. 接收正式 Content Processor 输入参数
2. 调用现有 prompt / style / llm 能力生成单个 content package
3. 对输出结构进行归一化，并提供安全兜底
"""

from __future__ import annotations

import json

from modules.content_processor.feedback_adapter import (
    apply_feedback_preferences,
)
from modules.content_processor.asset_selector_stub import build_selected_assets_plan
from modules.content_processor.candidate_asset_collector import build_candidate_assets_plan
from modules.content_processor.scene_scheduler_adapter import build_scheduler_ready_plan
from modules.content_processor.scene_assets_bridge_adapter import build_scene_assets_bridge_plan
from modules.content_processor.scene_bridge_adapter import build_scene_bridge_plan
from modules.content_processor.expression_builder import build_expression_package
from modules.content_processor.scene_builder import build_scene_package
from modules.content_processor.feedback_mapper import map_feedback, render_feedback_constraints
from modules.llm_client import call_llm
from modules.prompt_builder import build_prompt
from modules.style_prompt_enhancer import enhance_style_prompt


DEFAULT_SCRIPT_LENGTH_TARGET = 100


def _attach_expression_package(content_package: dict) -> dict:
    normalized_package = content_package if isinstance(content_package, dict) else {}
    package_with_expression = dict(normalized_package)
    package_with_expression["expression_package"] = build_expression_package(normalized_package)
    return package_with_expression


def _attach_scene_package(content_package: dict) -> dict:
    normalized_package = content_package if isinstance(content_package, dict) else {}
    expression_package = normalized_package.get("expression_package")
    package_with_scene = dict(normalized_package)
    package_with_scene["scene_package"] = build_scene_package(normalized_package, expression_package)
    return package_with_scene


def _attach_scene_bridge_plan(content_package: dict) -> dict:
    normalized_package = content_package if isinstance(content_package, dict) else {}
    scene_package = normalized_package.get("scene_package")
    package_with_bridge = dict(normalized_package)
    package_with_bridge["scene_bridge_plan"] = build_scene_bridge_plan(normalized_package, scene_package)
    return package_with_bridge


def _attach_scene_assets_bridge_plan(content_package: dict) -> dict:
    normalized_package = content_package if isinstance(content_package, dict) else {}
    scene_bridge_plan = normalized_package.get("scene_bridge_plan")
    package_with_assets_bridge = dict(normalized_package)
    package_with_assets_bridge["scene_assets_bridge_plan"] = build_scene_assets_bridge_plan(
        normalized_package,
        scene_bridge_plan,
    )
    return package_with_assets_bridge


def _attach_candidate_assets_plan(content_package: dict) -> dict:
    normalized_package = content_package if isinstance(content_package, dict) else {}
    scene_assets_bridge_plan = normalized_package.get("scene_assets_bridge_plan")
    package_with_candidates = dict(normalized_package)
    package_with_candidates["candidate_assets_plan"] = build_candidate_assets_plan(
        normalized_package,
        scene_assets_bridge_plan,
    )
    return package_with_candidates


def _attach_selected_assets_plan(content_package: dict) -> dict:
    normalized_package = content_package if isinstance(content_package, dict) else {}
    candidate_assets_plan = normalized_package.get("candidate_assets_plan")
    package_with_selected = dict(normalized_package)
    package_with_selected["selected_assets_plan"] = build_selected_assets_plan(
        normalized_package,
        candidate_assets_plan,
    )
    return package_with_selected


def _attach_scheduler_ready_plan(content_package: dict) -> dict:
    normalized_package = content_package if isinstance(content_package, dict) else {}
    selected_assets_plan = normalized_package.get("selected_assets_plan")
    package_with_scheduler_ready = dict(normalized_package)
    package_with_scheduler_ready["scheduler_ready_plan"] = build_scheduler_ready_plan(
        normalized_package,
        selected_assets_plan,
    )
    return package_with_scheduler_ready


def _attach_processing_layers(content_package: dict) -> dict:
    package_with_expression = _attach_expression_package(content_package)
    package_with_scene = _attach_scene_package(package_with_expression)
    package_with_bridge = _attach_scene_bridge_plan(package_with_scene)
    package_with_assets_bridge = _attach_scene_assets_bridge_plan(package_with_bridge)
    package_with_candidates = _attach_candidate_assets_plan(package_with_assets_bridge)
    package_with_selected = _attach_selected_assets_plan(package_with_candidates)
    return _attach_scheduler_ready_plan(package_with_selected)


def _normalize_script_length_target(value: int | str | None) -> int:
    try:
        normalized = int(value if value is not None else DEFAULT_SCRIPT_LENGTH_TARGET)
    except Exception:
        normalized = DEFAULT_SCRIPT_LENGTH_TARGET
    return max(50, min(normalized, 300))


def _normalize_reference_media(reference_media: dict | None) -> dict:
    normalized = reference_media if isinstance(reference_media, dict) else {}
    image_group = normalized.get("image_group") if isinstance(normalized.get("image_group"), dict) else None
    video_group = normalized.get("video_group") if isinstance(normalized.get("video_group"), dict) else None
    return {
        "image_group": image_group,
        "video_group": video_group,
    }


def _build_input_sources(reference_media: dict) -> dict:
    image_group = reference_media.get("image_group")
    video_group = reference_media.get("video_group")
    return {
        "has_reference_images": bool(image_group and image_group.get("assets")),
        "has_reference_videos": bool(video_group and video_group.get("assets")),
        "priority_policy": "user_uploaded_media_first",
        "image_group": image_group,
        "video_group": video_group,
    }


def _build_reference_media_section(reference_media: dict) -> str:
    image_group = reference_media.get("image_group")
    video_group = reference_media.get("video_group")
    lines = ["[Reference Media Inputs]"]

    if image_group and image_group.get("assets"):
        lines.extend(
            [
                "Image Group:",
                f"- count: {len(image_group.get('assets', []))}",
                f"- role: {image_group.get('role_hint', 'hook')}",
                f"- note: {image_group.get('note') or '未提供'}",
                "- note: these are user-provided immediate assets",
            ]
        )
    else:
        lines.extend(["Image Group:", "- count: 0", "- role: hook", "- note: none"])

    if video_group and video_group.get("assets"):
        lines.extend(
            [
                "Video Group:",
                f"- count: {len(video_group.get('assets', []))}",
                f"- role: {video_group.get('role_hint', 'primary')}",
                f"- note: {video_group.get('note') or '未提供'}",
                "- note: these are user-provided primary assets",
            ]
        )
    else:
        lines.extend(["Video Group:", "- count: 0", "- role: primary", "- note: none"])

    lines.append("这些参考素材拥有最高优先级，后续 Expression Processor 中应高于 keyword 匹配素材。")
    return "\n".join(lines)


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


def _parse_json_dict(raw_output: str) -> dict:
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


def _build_knowledge_package(parts: list[str], script_length_target: int, auto_flow: bool, reference_media: dict) -> dict:
    first = _clean_fragment(parts[0] if parts else "内容重点", max_length=20) or "内容重点"
    second = _clean_fragment(parts[1] if len(parts) > 1 else first, max_length=22) or first
    third = _clean_fragment(parts[2] if len(parts) > 2 else second, max_length=22) or second
    image_note = ((reference_media.get("image_group") or {}).get("note") or "").strip()
    video_note = ((reference_media.get("video_group") or {}).get("note") or "").strip()
    media_line = _clean_fragment(image_note or video_note, max_length=24)

    return {
        "title": f"本质上，关键在于{second}".rstrip("，,。；;：:、 "),
        "script": _dedupe_keep_order(
            [
                f"本质上，不是只看{first}。",
                f"如果结合参考素材，重点要围绕{media_line}展开。" if media_line else "",
                f"关键在于{second}。",
                f"不是停在表面变化，而是回到{third}。",
            ]
        )[:3],
        "highlights": _dedupe_keep_order(
            [
                f"本质上，不是只看{first}",
                media_line,
                f"关键在于{second}",
                f"不是表面变化，而是{third}",
            ]
        )[:3],
        "keywords": _dedupe_keep_order(
            [first, second, third, media_line, "解释型", f"长度{script_length_target}", "auto" if auto_flow else "manual"]
        )[:6],
    }


def _build_authority_package(parts: list[str], script_length_target: int, auto_flow: bool, reference_media: dict) -> dict:
    subject = _extract_focus_subject(parts)
    second = _clean_fragment(parts[1] if len(parts) > 1 else parts[0] if parts else "核心条件", max_length=22) or "核心条件"
    third = _clean_fragment(parts[2] if len(parts) > 2 else second, max_length=18) or second
    video_note = ((reference_media.get("video_group") or {}).get("note") or "").strip()
    image_note = ((reference_media.get("image_group") or {}).get("note") or "").strip()
    media_line = _clean_fragment(video_note or image_note, max_length=22)

    return {
        "title": f"不要只看{subject}".rstrip("，,。；;：:、 "),
        "script": _dedupe_keep_order(
            [
                f"不要只盯{subject}。",
                f"参考素材直接服务于{media_line}。" if media_line else "",
                f"真正重要的是{second}。",
                f"核心不是表面变化，而是{third}。",
            ]
        )[:3],
        "highlights": _dedupe_keep_order(
            [
                f"不要只看{subject}",
                media_line,
                f"真正重要的是{second}",
                f"核心是{third}",
            ]
        )[:3],
        "keywords": _dedupe_keep_order(
            [subject, second, third, media_line, "判断型", f"长度{script_length_target}", "auto" if auto_flow else "manual"]
        )[:6],
    }


def _build_story_package(parts: list[str], script_length_target: int, auto_flow: bool, reference_media: dict) -> dict:
    subject = _extract_focus_subject(parts)
    first = _clean_fragment(parts[0] if parts else subject, max_length=20) or subject
    second = _clean_fragment(parts[1] if len(parts) > 1 else first, max_length=22) or first
    third = _clean_fragment(parts[2] if len(parts) > 2 else second, max_length=18) or second
    image_note = ((reference_media.get("image_group") or {}).get("note") or "").strip()
    video_note = ((reference_media.get("video_group") or {}).get("note") or "").strip()
    media_line = _clean_fragment(image_note or video_note, max_length=22)

    return {
        "title": f"很多人先看{subject}，但关键不止这一层".rstrip("，,。；;：:、 "),
        "script": _dedupe_keep_order(
            [
                f"很多人一上来就盯着{first}。",
                f"如果参考素材要进场，先让它承接{media_line}。" if media_line else "",
                f"但真正拉开差距的，是{second}。",
                f"再往下看，关键落在{third}。",
            ]
        )[:3],
        "highlights": _dedupe_keep_order(
            [
                f"很多人先看{first}",
                media_line,
                f"但关键是{second}",
                f"真正落点在{third}",
            ]
        )[:3],
        "keywords": _dedupe_keep_order(
            [subject, second, third, media_line, "转折型", f"长度{script_length_target}", "auto" if auto_flow else "manual"]
        )[:6],
    }


def _build_product_package(parts: list[str], script_length_target: int, auto_flow: bool, reference_media: dict) -> dict:
    first = _clean_fragment(parts[0] if parts else "核心卖点", max_length=18) or "核心卖点"
    second = _clean_fragment(parts[1] if len(parts) > 1 else first, max_length=20) or first
    third = _clean_fragment(parts[2] if len(parts) > 2 else second, max_length=18) or second
    media_line = _clean_fragment(((reference_media.get("video_group") or {}).get("note") or (reference_media.get("image_group") or {}).get("note") or ""), max_length=22)

    return {
        "title": f"先把{first}整理成可确认内容包".rstrip("，,。；;：:、 "),
        "script": _dedupe_keep_order(
            [
                f"先把{first}说清楚。",
                f"参考素材优先服务于{media_line}。" if media_line else "",
                f"再把{second}整理成稳定表达。",
                f"最后把{third}作为后续承接重点。",
            ]
        )[:3],
        "highlights": _dedupe_keep_order([first, media_line, second, third])[:3],
        "keywords": _dedupe_keep_order(
            [first, second, third, media_line, "产品型", f"长度{script_length_target}", "auto" if auto_flow else "manual"]
        )[:6],
    }


def _build_ads_package(parts: list[str], script_length_target: int, auto_flow: bool, reference_media: dict) -> dict:
    first = _clean_fragment(parts[0] if parts else "关键信息", max_length=18) or "关键信息"
    second = _clean_fragment(parts[1] if len(parts) > 1 else first, max_length=18) or first
    third = _clean_fragment(parts[2] if len(parts) > 2 else second, max_length=18) or second
    media_line = _clean_fragment(((reference_media.get("image_group") or {}).get("note") or (reference_media.get("video_group") or {}).get("note") or ""), max_length=22)

    return {
        "title": f"{first}，先抓主信息再往下走".rstrip("，,。；;：:、 "),
        "script": _dedupe_keep_order(
            [
                f"先把{first}抬出来。",
                f"参考素材优先强化{media_line}。" if media_line else "",
                f"再把{second}压缩成可记住的一句话。",
                f"最后用{third}完成收束。",
            ]
        )[:3],
        "highlights": _dedupe_keep_order([first, media_line, second, third])[:3],
        "keywords": _dedupe_keep_order(
            [first, second, third, media_line, "广告型", f"长度{script_length_target}", "auto" if auto_flow else "manual"]
        )[:6],
    }


def _build_fallback_package(raw_text: str, content_mode: str, style_mode: str, script_length_target: int, auto_flow: bool, reference_media: dict) -> dict:
    parts = _split_raw_parts(raw_text)
    style_key = str(style_mode or "").strip().lower()
    if style_key == "authority":
        normalized = _build_authority_package(parts, script_length_target, auto_flow, reference_media)
    elif style_key == "story":
        normalized = _build_story_package(parts, script_length_target, auto_flow, reference_media)
    elif style_key == "product":
        normalized = _build_product_package(parts, script_length_target, auto_flow, reference_media)
    elif style_key == "ads":
        normalized = _build_ads_package(parts, script_length_target, auto_flow, reference_media)
    else:
        normalized = _build_knowledge_package(parts, script_length_target, auto_flow, reference_media)

    return {
        "content_mode": content_mode,
        "style_mode": style_mode,
        "title": normalized["title"] or "内容重点",
        "script": normalized["script"][:3] or ["先提取主信息。", "再整理核心关系。", "最后形成可确认内容包。"],
        "highlights": normalized["highlights"][:3] or ["内容重点", "核心关系", "确认草稿"],
        "keywords": normalized["keywords"][:6] or [content_mode, style_mode, "draft", "content package"],
        "meta": {
            "script_length_target": script_length_target,
            "confirm_status": "draft",
            "auto_flow": bool(auto_flow),
        },
        "input_sources": _build_input_sources(reference_media),
    }


def _build_formal_content_package_prompt(
    raw_text: str,
    content_mode: str,
    style_mode: str,
    script_length_target: int,
    feedback_constraints: dict,
    reference_media: dict,
) -> str:
    base_prompt = build_prompt(
        raw_text=raw_text,
        content_mode=content_mode,
        style_mode=style_mode,
        user_intent={"script_length_target": script_length_target} if script_length_target else None,
    )
    enhanced_prompt = enhance_style_prompt(style_mode, base_prompt["prompt"])

    feedback_section = render_feedback_constraints(feedback_constraints)
    if feedback_section:
        feedback_section = f"{feedback_section}\n\n"

    reference_section = _build_reference_media_section(reference_media)

    return (
        f"{enhanced_prompt}\n\n"
        f"{reference_section}\n\n"
        "[正式 Content Package 任务]\n"
        "请严格基于原文，输出单个正式 content package，不要输出旧 demo 结构。\n"
        f"content_mode={content_mode}\n"
        f"style_mode={style_mode}\n"
        f"script_length_target={script_length_target}\n"
        f"{feedback_section}"
        "必须输出严格 JSON，结构固定为：\n"
        '{"title":"...","script":["...","...","..."],"highlights":["...","...","..."],"keywords":["...","...","...","..."]}\n'
        "要求：\n"
        "1. title 简短、可读、适合内容处理确认界面。\n"
        "2. script 输出 3 句左右，作为声音轴，不要太碎。\n"
        "3. highlights 输出 3 条左右，适合上屏。\n"
        "4. keywords 输出 4 到 6 个，既包含主题词，也包含语义标签。\n"
        "4.1 如果用户提供了参考素材 note / role，必须把这些意图串进 title / script / highlights / keywords。\n"
        "5. 所有内容必须紧贴原文，不得编造新事实。\n"
        "6. 不要输出 highlight、results、scenes、prompt_summary 等旧字段。"
    )


def _normalize_string_list(value, minimum_count: int, fallback_items: list[str], max_length: int = 28) -> list[str]:
    items: list[str] = []
    if isinstance(value, list):
        items = [_clean_fragment(item, max_length=max_length) for item in value]
    elif isinstance(value, str):
        items = [_clean_fragment(item, max_length=max_length) for item in value.split("\n")]

    cleaned = _dedupe_keep_order([item for item in items if item])
    if len(cleaned) >= minimum_count:
        return cleaned

    merged = _dedupe_keep_order(cleaned + fallback_items)
    return merged[: max(minimum_count, len(merged))]


def _normalize_content_package_payload(
    payload: dict,
    fallback_package: dict,
    script_length_target: int,
    auto_flow: bool,
    reference_media: dict,
) -> dict:
    normalized = payload if isinstance(payload, dict) else {}

    title = _clean_fragment(normalized.get("title") or fallback_package["title"], max_length=28) or fallback_package["title"]
    script = _normalize_string_list(normalized.get("script"), 3, fallback_package["script"], max_length=36)[:3]
    highlights = _normalize_string_list(normalized.get("highlights"), 3, fallback_package["highlights"], max_length=24)[:3]
    keywords = _normalize_string_list(normalized.get("keywords"), 4, fallback_package["keywords"], max_length=18)[:6]

    return {
        "content_mode": fallback_package["content_mode"],
        "style_mode": fallback_package["style_mode"],
        "title": title,
        "script": script,
        "highlights": highlights,
        "keywords": keywords,
        "meta": {
            "script_length_target": script_length_target,
            "confirm_status": "draft",
            "auto_flow": bool(auto_flow),
        },
        "input_sources": _build_input_sources(reference_media),
    }


def _is_grounded_content_package(content_package: dict, raw_text: str) -> bool:
    source = _compact_text(raw_text)
    if len(source) < 4:
        return True

    combined = _compact_text(content_package.get("title", ""))
    for item in content_package.get("script", []):
        combined += _compact_text(item)
    for item in content_package.get("highlights", []):
        combined += _compact_text(item)

    if not combined:
        return False

    for index in range(len(source) - 3):
        fragment = source[index:index + 4]
        if fragment and fragment in combined:
            return True
    return False


def build_content_package(
    raw_text: str,
    content_mode: str,
    style_mode: str,
    script_length_target: int = DEFAULT_SCRIPT_LENGTH_TARGET,
    feedback_text: str = "",
    auto_flow: bool = False,
    reference_media: dict | None = None,
) -> dict:
    raw_text_value = str(raw_text or "").strip()
    content_mode_value = str(content_mode or "finance").strip().lower() or "finance"
    style_mode_value = str(style_mode or "knowledge").strip().lower() or "knowledge"
    normalized_length_target = _normalize_script_length_target(script_length_target)
    feedback_value = str(feedback_text or "").strip()
    auto_flow_value = bool(auto_flow)
    reference_media_value = _normalize_reference_media(reference_media)
    feedback_constraints = map_feedback(feedback_value)

    fallback_package = _build_fallback_package(
        raw_text=raw_text_value,
        content_mode=content_mode_value,
        style_mode=style_mode_value,
        script_length_target=normalized_length_target,
        auto_flow=auto_flow_value,
        reference_media=reference_media_value,
    )
    fallback_package = apply_feedback_preferences(fallback_package, feedback_constraints, style_mode_value)
    fallback_package = _attach_processing_layers(fallback_package)

    prompt = _build_formal_content_package_prompt(
        raw_text=raw_text_value,
        content_mode=content_mode_value,
        style_mode=style_mode_value,
        script_length_target=normalized_length_target,
        feedback_constraints=feedback_constraints,
        reference_media=reference_media_value,
    )

    try:
        raw_output = call_llm(prompt)
        payload = _parse_json_dict(raw_output)
        normalized_package = _normalize_content_package_payload(
            payload=payload,
            fallback_package=fallback_package,
            script_length_target=normalized_length_target,
            auto_flow=auto_flow_value,
            reference_media=reference_media_value,
        )
        normalized_package = apply_feedback_preferences(normalized_package, feedback_constraints, style_mode_value)
        normalized_package = _attach_processing_layers(normalized_package)
        if not _is_grounded_content_package(normalized_package, raw_text_value):
            return fallback_package
        return normalized_package
    except Exception:
        return fallback_package