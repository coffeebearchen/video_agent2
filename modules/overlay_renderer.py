from __future__ import annotations

import os
import re
from typing import List, Optional

from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import CompositeVideoClip, ImageClip, vfx


TITLE_TEXT_COLOR = (248, 249, 250, 255)
KEYWORD_TEXT_COLOR = (255, 179, 71, 255)
TEXT_STROKE_COLOR = (18, 18, 18, 220)
TITLE_BG_COLOR = (10, 10, 10, 145)
KEYWORD_BG_COLOR = (25, 25, 25, 190)
TITLE_POSITION_Y = 96
HIGHLIGHT_POSITION_RATIO_Y = 0.42
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


def build_title_text(scene_text: str) -> str:
    sentences = _split_sentences(scene_text)
    if sentences:
        return _truncate_text(sentences[0], 20)
    return _truncate_text(scene_text, 20)


def build_conclusion_text(scene_text: str) -> str:
    sentences = _split_sentences(scene_text)
    if len(sentences) >= 2:
        return _truncate_text(sentences[-1], 28)
    if sentences:
        return _truncate_text(sentences[0], 28)
    return _truncate_text(scene_text, 28)


def build_bilingual_highlight_text(highlight_text: str) -> str:
    chinese = str(highlight_text or "").strip()
    if not chinese:
        return ""
    english = TRANSLATION_MAP.get(chinese, "")
    if english:
        return f"{chinese}\n{english}"
    return chinese


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
    title_text = build_title_text(scene_text)
    highlights = normalize_highlights(scene_highlights, limit=1)
    primary_highlight = highlights[0] if highlights else None
    bilingual_highlight = build_bilingual_highlight_text(primary_highlight)

    overlay_clips = [base_clip]
    title_clip = None
    highlight_clip = None
    print(f"[OVERLAY] title={title_text}")
    print(f"[OVERLAY] highlight={primary_highlight or ''}")

    title_path = build_text_overlay_image(
        os.path.join(normalized_dir, f"overlay_title_{scene_index_zero_based:03d}.png"),
        title_text,
        fonts_dir,
        58,
        min(target_w - 120, 920),
        TITLE_TEXT_COLOR,
        TITLE_BG_COLOR,
    )
    if title_path:
        title_clip = (
            ImageClip(title_path)
            .set_start(0)
            .set_duration(duration)
            .set_position(("center", TITLE_POSITION_Y))
        )

    if bilingual_highlight:
        desired_highlight_start = max(0.8, duration * 0.35)
        desired_highlight_duration = min(3.0, duration * 0.6)
        highlight_path = build_text_overlay_image(
            os.path.join(normalized_dir, f"overlay_keyword_{scene_index_zero_based:03d}_0.png"),
            bilingual_highlight,
            fonts_dir,
            60,
            min(target_w - 180, 760),
            KEYWORD_TEXT_COLOR,
            KEYWORD_BG_COLOR,
        )
        if highlight_path:
            highlight_start, highlight_duration = _clamp_window(
                desired_highlight_start,
                desired_highlight_duration,
                duration,
            )
            print(f"[OVERLAY] highlight_start={highlight_start:.2f}")
            print(f"[OVERLAY] highlight_duration={highlight_duration:.2f}")
            highlight_clip = (
                ImageClip(highlight_path)
                .set_start(highlight_start)
                .set_duration(highlight_duration)
                .set_position(("center", max(220, int(target_h * HIGHLIGHT_POSITION_RATIO_Y))))
            )

    if title_clip is not None:
        overlay_clips.append(title_clip)

    if highlight_clip is not None:
        overlay_clips.append(_apply_fade(highlight_clip, highlight_clip.duration))

    if len(overlay_clips) == 1:
        return base_clip

    composite = CompositeVideoClip(overlay_clips, size=(target_w, target_h)).set_duration(duration)
    if getattr(base_clip, "audio", None) is not None:
        composite = composite.set_audio(base_clip.audio)
    return composite