from __future__ import annotations

import os
import re
from typing import List, Optional

from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import CompositeVideoClip, ImageClip, vfx

from modules.expression_alignment import align_scene_expression, emit_expression_alignment_logs
from modules.overlay_style_engine import (
    build_highlight_display_text,
    emit_text_spec_debug,
    get_runtime_style_name,
    get_highlight_spec,
    get_overlay_style,
    get_title_spec,
    normalize_highlight_count,
    resolve_title_timing,
)


TEXT_STROKE_COLOR = (18, 18, 18, 220)
TRANSLATION_MAP = {
    "提高生产效率": "Increase Efficiency",
    "降低人工成本": "Reduce Labor Cost",
    "自动化系统": "Automation System",
    "传统设备效率低": "Low Efficiency",
    "提高连续生产稳定性": "Improve Production Stability",
    "减少人工波动": "Reduce Manual Variance",
    "控制能力": "Control Capability",
    "提高效率": "Increase Efficiency",
    "降低停机风险": "Reduce Downtime Risk",
    "更容易保持连续生产": "Sustain Continuous Output",
}


def _font_candidates(fonts_dir: str) -> List[str]:
    return [
        os.path.join(fonts_dir, "SourceHanSansCN-Bold.otf"),
        os.path.join(fonts_dir, "SourceHanSansSC-Regular.otf"),
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/arial.ttf",
    ]


def _load_font(fonts_dir: str, size: int):
    for candidate in _font_candidates(fonts_dir):
        if candidate and os.path.exists(candidate):
            try:
                return ImageFont.truetype(candidate, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _clean_text(text: str) -> str:
    return " ".join(str(text or "").replace("\n", " ").split())


def _clean_multiline_text(text: str) -> str:
    lines = []
    for line in str(text or "").split("\n"):
        cleaned_line = " ".join(line.split()).strip()
        if cleaned_line:
            lines.append(cleaned_line)
    return "\n".join(lines)


def _split_sentences(text: str) -> List[str]:
    cleaned = _clean_text(text)
    if not cleaned:
        return []
    parts = re.findall(r"[^。！？!?；;]+[。！？!?；;]?", cleaned)
    return [part.strip() for part in parts if part.strip()]


def _truncate_text(text: str, limit: int) -> str:
    normalized = _clean_text(text)
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit].rstrip() + "..."


def build_title_text(scene_text: str, max_chars: int = 20) -> str:
    sentences = _split_sentences(scene_text)
    if sentences:
        return _truncate_text(sentences[0], max_chars)
    return _truncate_text(scene_text, max_chars)


def build_conclusion_text(scene_text: str) -> str:
    sentences = _split_sentences(scene_text)
    if len(sentences) >= 2:
        return _truncate_text(sentences[-1], 28)
    if sentences:
        return _truncate_text(sentences[0], 28)
    return _truncate_text(scene_text, 28)


def build_bilingual_highlight_text(highlight_text: str, style_name: str = "creator_clean") -> str:
    chinese = str(highlight_text or "").strip()
    if not chinese:
        return ""
    english = TRANSLATION_MAP.get(chinese, "")
    return build_highlight_display_text(chinese, english, style_name=style_name)


def normalize_highlights(scene_highlights: List[str], limit: int = 1) -> List[str]:
    results: List[str] = []
    for item in scene_highlights or []:
        word = str(item or "").strip()
        if not word or word in results:
            continue
        results.append(word)
        if len(results) >= limit:
            break
    return results


def _measure_text(draw: ImageDraw.ImageDraw, text: str, font) -> tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=2)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> List[str]:
    if not text:
        return []

    lines: List[str] = []
    for paragraph in str(text or "").split("\n"):
        if not paragraph:
            continue

        current = ""
        for char in paragraph:
            candidate = current + char
            width, _ = _measure_text(draw, candidate, font)
            if current and width > max_width:
                lines.append(current)
                current = char
            else:
                current = candidate

        if current:
            lines.append(current)
    return lines


def build_text_overlay_image(
    output_path: str,
    text: str,
    fonts_dir: str,
    font_size: int,
    max_width: int,
    text_color: tuple[int, int, int, int],
    bg_color: tuple[int, int, int, int],
    align: str = "center",
    padding_x: int = 28,
    padding_y: int = 20,
    radius: int = 24,
) -> Optional[str]:
    content = _clean_multiline_text(text)
    if not content:
        return None

    parent_dir = os.path.dirname(output_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)

    font = _load_font(fonts_dir, font_size)
    draft = Image.new("RGBA", (max_width, 400), (0, 0, 0, 0))
    draft_draw = ImageDraw.Draw(draft)
    wrapped = _wrap_text(draft_draw, content, font, max_width - padding_x * 2)
    if not wrapped:
        return None

    line_heights = []
    text_width = 0
    for line in wrapped:
        width, height = _measure_text(draft_draw, line, font)
        line_heights.append(height)
        text_width = max(text_width, width)

    line_gap = max(10, int(font_size * 0.22))
    text_height = sum(line_heights) + max(0, len(line_heights) - 1) * line_gap
    image_width = min(max_width, text_width + padding_x * 2)
    image_height = text_height + padding_y * 2

    canvas = Image.new("RGBA", (image_width, image_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        [(0, 0), (image_width - 1, image_height - 1)],
        radius=radius,
        fill=bg_color,
    )

    current_y = padding_y
    for line, line_height in zip(wrapped, line_heights):
        line_width, _ = _measure_text(draw, line, font)
        if align == "left":
            line_x = padding_x
        else:
            line_x = (image_width - line_width) // 2

        draw.text(
            (line_x, current_y),
            line,
            font=font,
            fill=text_color,
            stroke_width=2,
            stroke_fill=TEXT_STROKE_COLOR,
        )
        current_y += line_height + line_gap

    canvas.save(output_path, format="PNG")
    return output_path


def _apply_fade(clip, duration: float):
    fade_time = min(0.18, max(0.08, duration * 0.2))
    result = clip.fx(vfx.fadein, fade_time)
    try:
        result = result.fx(vfx.fadeout, fade_time)
    except Exception:
        pass
    return result


def _clamp_window(start: float, desired_duration: float, total_duration: float) -> tuple[float, float]:
    safe_start = max(0.0, min(start, max(0.0, total_duration - 0.1)))
    safe_duration = max(0.1, min(desired_duration, max(0.1, total_duration - safe_start)))
    return safe_start, safe_duration


def apply_scene_expression_overlay(
    base_clip,
    scene_index_zero_based: int,
    scene_text: str,
    scene_highlights: List[str],
    duration: float,
    normalized_dir: str,
    target_w: int,
    target_h: int,
    fonts_dir: str,
):
    style_name = get_runtime_style_name()
    style = get_overlay_style(style_name)
    title_spec = get_title_spec(style_name)
    highlight_spec = get_highlight_spec(style_name)

    highlights = normalize_highlight_count(scene_highlights, style_name=style_name)
    alignment_result = align_scene_expression(
        scene_id=scene_index_zero_based,
        scene_text=scene_text,
        scene_highlights=highlights,
        scene_duration=duration,
        style_name=style_name,
        title_max_chars=int(title_spec.get("max_chars", 20) or 20),
    )
    emit_expression_alignment_logs(alignment_result)

    title_text = str(alignment_result.get("title_final", "") or "")
    primary_highlight = str(alignment_result.get("highlight_final", "") or "") or None
    bilingual_highlight = build_bilingual_highlight_text(primary_highlight, style_name=style_name)

    overlay_clips = [base_clip]
    title_clip = None
    highlight_clip = None
    print(f"[OVERLAY_STYLE] style_name={style_name}")
    emit_text_spec_debug(style_name)
    print(f"[OVERLAY_STYLE] title_mode={title_spec.get('mode', 'persistent')}")
    print(f"[OVERLAY_STYLE] highlight_mode={highlight_spec.get('display_mode', 'single_card')}")
    print(f"[OVERLAY_STYLE] highlight_max_count={highlight_spec.get('max_count', 1)}")
    print(f"[OVERLAY_STYLE] bilingual_mode={highlight_spec.get('bilingual_mode', 'zh_en_stacked')}")
    print(f"[OVERLAY] title={title_text}")
    print(f"[OVERLAY] highlight={primary_highlight or ''}")

    if title_spec.get("enabled", True):
        title_path = build_text_overlay_image(
            os.path.join(normalized_dir, f"overlay_title_{scene_index_zero_based:03d}.png"),
            title_text,
            fonts_dir,
            int(title_spec.get("font_size", 58) or 58),
            min(target_w - 120, int(title_spec.get("max_width", 920) or 920)),
            tuple(title_spec.get("text_color", (248, 249, 250, 255))),
            tuple(title_spec.get("bg_color", (10, 10, 10, 145))),
            padding_x=int(title_spec.get("padding_x", 28) or 28),
            padding_y=int(title_spec.get("padding_y", 20) or 20),
            radius=int(title_spec.get("radius", 24) or 24),
        )
        if title_path:
            title_start, title_duration = resolve_title_timing(duration, style_name=style_name)
            title_clip = (
                ImageClip(title_path)
                .set_start(title_start)
                .set_duration(title_duration)
                .set_position(("center", int(title_spec.get("position_y", 96) or 96)))
            )

    if highlight_spec.get("enabled", True) and bilingual_highlight:
        highlight_path = build_text_overlay_image(
            os.path.join(normalized_dir, f"overlay_keyword_{scene_index_zero_based:03d}_0.png"),
            bilingual_highlight,
            fonts_dir,
            int(highlight_spec.get("font_size", 60) or 60),
            min(target_w - 180, int(highlight_spec.get("max_width", 760) or 760)),
            tuple(highlight_spec.get("text_color", (255, 179, 71, 255))),
            tuple(highlight_spec.get("bg_color", (25, 25, 25, 190))),
            padding_x=int(highlight_spec.get("padding_x", 28) or 28),
            padding_y=int(highlight_spec.get("padding_y", 20) or 20),
            radius=int(highlight_spec.get("radius", 24) or 24),
        )
        if highlight_path:
            highlight_start = float(alignment_result.get("highlight_start", 0.0) or 0.0)
            highlight_duration = float(alignment_result.get("highlight_duration", 0.0) or 0.0)
            print(f"[OVERLAY] highlight_start={highlight_start:.2f}")
            print(f"[OVERLAY] highlight_duration={highlight_duration:.2f}")
            highlight_clip = (
                ImageClip(highlight_path)
                .set_start(highlight_start)
                .set_duration(highlight_duration)
                .set_position(("center", max(220, int(target_h * float(highlight_spec.get("position_ratio_y", 0.42) or 0.42)))))
            )

    if title_clip is not None:
        overlay_clips.append(title_clip)

    if highlight_clip is not None:
        if highlight_spec.get("fade_enabled", True):
            overlay_clips.append(_apply_fade(highlight_clip, highlight_clip.duration))
        else:
            overlay_clips.append(highlight_clip)

    if len(overlay_clips) == 1:
        return base_clip

    composite = CompositeVideoClip(overlay_clips, size=(target_w, target_h)).set_duration(duration)
    if getattr(base_clip, "audio", None) is not None:
        composite = composite.set_audio(base_clip.audio)
    return composite