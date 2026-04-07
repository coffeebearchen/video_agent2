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
from modules.style_content_link import apply_style_content_link


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


def _split_bilingual_text(bilingual_text: str) -> tuple[str, str]:
    """
    Extract zh and en from bilingual text.
    Supports:
    - "zhtext\nen_text" (stacked: newline separator)
    - "zhtext / en_text" (inline: slash separator)
    - "zh_text_only" (zh only, no en)
    """
    bilingual_text = str(bilingual_text or "").strip()
    
    # Try newline separator (stacked)
    if "\n" in bilingual_text:
        parts = bilingual_text.split("\n", 1)
        zh_text = str(parts[0] or "").strip()
        en_text = str(parts[1] or "").strip() if len(parts) > 1 else ""
        return zh_text, en_text
    
    # Try slash separator (inline)
    if " / " in bilingual_text:
        parts = bilingual_text.split(" / ", 1)
        zh_text = str(parts[0] or "").strip()
        en_text = str(parts[1] or "").strip() if len(parts) > 1 else ""
        return zh_text, en_text
    
    # Fallback: treat entire text as zh_text
    return bilingual_text, ""


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
    """
    Legacy single-text highlight overlay.
    Used when bilingual mode is disabled or bilingual render fails (fallback).
    """
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


def build_bilingual_highlight_image(
    output_path: str,
    bilingual_text: str,
    fonts_dir: str,
    highlight_spec: dict,
) -> Optional[str]:
    """
    V1 Bilingual highlighting: split zh/en, render separately with independent color/size.
    
    Supported layouts:
    - zh_en_stacked: zh on top, en below (default)
    - zh_en_inline: zh on left, en on right
    - zh_only: only zh
    - en_only: only en
    
    Fallback: if bilingual_render_enabled is False or render fails, 
    returns None to signal use of legacy build_text_overlay_image().
    """
    # Check if bilingual render is enabled
    if not highlight_spec.get("bilingual_render_enabled", True):
        return None  # Signal to use legacy mode
    
    try:
        parent_dir = os.path.dirname(output_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        
        # Extract zh and en
        zh_text, en_text = _split_bilingual_text(bilingual_text)
        zh_text = str(zh_text or "").strip()
        en_text = str(en_text or "").strip()
        
        # Determine layout
        layout = str(highlight_spec.get("zh_en_layout", "zh_en_stacked") or "zh_en_stacked").lower()
        
        # Handle zh_only / en_only cases
        if layout == "zh_only":
            en_text = ""
        elif layout == "en_only":
            zh_text = ""
        
        # If no text at all, fail gracefully
        if not zh_text and not en_text:
            return None
        
        # Configure colors and fonts
        zh_color = tuple(highlight_spec.get("zh_text_color", None) or highlight_spec.get("text_color", (255, 179, 71, 255)))
        en_color = tuple(highlight_spec.get("en_text_color", None) or highlight_spec.get("text_color", (255, 179, 71, 255)))
        
        zh_font_size = int(highlight_spec.get("zh_font_size", None) or highlight_spec.get("font_size", 60) or 60)
        en_font_size = int(highlight_spec.get("en_font_size", None) or highlight_spec.get("font_size", 60) or 60)
        
        gap = int(highlight_spec.get("zh_en_gap", 10) or 10)
        
        zh_font = _load_font(fonts_dir, zh_font_size)
        en_font = _load_font(fonts_dir, en_font_size)
        
        max_width = int(highlight_spec.get("max_width", 760) or 760)
        padding_x = int(highlight_spec.get("padding_x", 28) or 28)
        padding_y = int(highlight_spec.get("padding_y", 20) or 20)
        radius = int(highlight_spec.get("radius", 24) or 24)
        bg_color = tuple(highlight_spec.get("bg_color", (25, 25, 25, 190)))
        
        # Measure zh and en blocks
        draft = Image.new("RGBA", (max_width, 500), (0, 0, 0, 0))
        draft_draw = ImageDraw.Draw(draft)
        
        zh_wrapped = _wrap_text(draft_draw, zh_text, zh_font, max_width - padding_x * 2) if zh_text else []
        en_wrapped = _wrap_text(draft_draw, en_text, en_font, max_width - padding_x * 2) if en_text else []
        
        # Calculate dimensions for stacked layout
        if layout in ("zh_en_stacked", ""):  # Default is stacked
            # Measure each text block
            zh_lines_heights = []
            zh_width = 0
            for line in zh_wrapped:
                w, h = _measure_text(draft_draw, line, zh_font)
                zh_lines_heights.append(h)
                zh_width = max(zh_width, w)
            
            en_lines_heights = []
            en_width = 0
            for line in en_wrapped:
                w, h = _measure_text(draft_draw, line, en_font)
                en_lines_heights.append(h)
                en_width = max(en_width, w)
            
            line_gap = max(8, int(zh_font_size * 0.18))
            zh_height = sum(zh_lines_heights) + max(0, len(zh_lines_heights) - 1) * line_gap if zh_wrapped else 0
            en_height = sum(en_lines_heights) + max(0, len(en_lines_heights) - 1) * line_gap if en_wrapped else 0
            
            total_text_width = max(zh_width, en_width)
            total_text_height = zh_height + (gap if zh_height > 0 and en_height > 0 else 0) + en_height
            
            card_width = min(max_width, total_text_width + padding_x * 2)
            card_height = total_text_height + padding_y * 2
            
            # Create canvas
            canvas = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(canvas)
            draw.rounded_rectangle(
                [(0, 0), (card_width - 1, card_height - 1)],
                radius=radius,
                fill=bg_color,
            )
            
            current_y = padding_y
            
            # Draw zh text
            for line, line_height in zip(zh_wrapped, zh_lines_heights):
                line_width, _ = _measure_text(draw, line, zh_font)
                line_x = (card_width - line_width) // 2
                draw.text(
                    (line_x, current_y),
                    line,
                    font=zh_font,
                    fill=zh_color,
                    stroke_width=2,
                    stroke_fill=TEXT_STROKE_COLOR,
                )
                current_y += line_height + line_gap
            
            # Add gap
            if zh_height > 0 and en_height > 0:
                current_y += gap - line_gap
            
            # Draw en text
            for line, line_height in zip(en_wrapped, en_lines_heights):
                line_width, _ = _measure_text(draw, line, en_font)
                line_x = (card_width - line_width) // 2
                draw.text(
                    (line_x, current_y),
                    line,
                    font=en_font,
                    fill=en_color,
                    stroke_width=2,
                    stroke_fill=TEXT_STROKE_COLOR,
                )
                current_y += line_height + line_gap
        
        elif layout == "zh_en_inline":
            # Inline layout: zh on left, en on right, same baseline
            zh_lines_heights = []
            zh_width = 0
            for line in zh_wrapped:
                w, h = _measure_text(draft_draw, line, zh_font)
                zh_lines_heights.append(h)
                zh_width = max(zh_width, w)
            
            en_lines_heights = []
            en_width = 0
            for line in en_wrapped:
                w, h = _measure_text(draft_draw, line, en_font)
                en_lines_heights.append(h)
                en_width = max(en_width, w)
            
            line_gap = max(8, int(zh_font_size * 0.18))
            zh_height = sum(zh_lines_heights) + max(0, len(zh_lines_heights) - 1) * line_gap if zh_wrapped else 0
            en_height = sum(en_lines_heights) + max(0, len(en_lines_heights) - 1) * line_gap if en_wrapped else 0
            max_height = max(zh_height, en_height)
            
            total_text_width = zh_width + (gap if zh_width > 0 and en_width > 0 else 0) + en_width
            total_text_height = max_height
            
            card_width = min(max_width, total_text_width + padding_x * 2)
            card_height = total_text_height + padding_y * 2
            
            # Create canvas
            canvas = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(canvas)
            draw.rounded_rectangle(
                [(0, 0), (card_width - 1, card_height - 1)],
                radius=radius,
                fill=bg_color,
            )
            
            current_x = padding_x
            current_y = padding_y + (max_height - zh_height) // 2  # Vertical center
            
            # Draw zh text
            for line in zh_wrapped:
                draw.text(
                    (current_x, current_y),
                    line,
                    font=zh_font,
                    fill=zh_color,
                    stroke_width=2,
                    stroke_fill=TEXT_STROKE_COLOR,
                )
                line_height = _measure_text(draw, line, zh_font)[1]
                current_y += line_height + line_gap
            
            # Draw en text
            current_x = padding_x + zh_width + (gap if zh_width > 0 and en_width > 0 else 0)
            current_y = padding_y + (max_height - en_height) // 2  # Vertical center
            
            for line in en_wrapped:
                draw.text(
                    (current_x, current_y),
                    line,
                    font=en_font,
                    fill=en_color,
                    stroke_width=2,
                    stroke_fill=TEXT_STROKE_COLOR,
                )
                line_height = _measure_text(draw, line, en_font)[1]
                current_y += line_height + line_gap
        
        else:
            # Unknown layout, fail gracefully
            return None
        
        canvas.save(output_path, format="PNG")
        return output_path
    
    except Exception as e:
        print(f"[BILINGUAL_RENDER] error={e}, falling back to legacy mode")
        return None


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

    styled_content = apply_style_content_link(
        style_name=style_name,
        title=str(alignment_result.get("title_final", "") or ""),
        highlight=str(alignment_result.get("highlight_final", "") or ""),
    )

    title_text = str(styled_content.get("title", "") or "")
    primary_highlight = str(styled_content.get("highlight", "") or "") or None
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
    print(f"[OVERLAY_STYLE] bilingual_render_enabled={highlight_spec.get('bilingual_render_enabled', True)}")
    print(f"[STYLE_CONTENT] style_name={style_name}")
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

    # V1 Bilingual rendering: try bilingual first, fallback to legacy if disabled/failed
    if highlight_spec.get("enabled", True) and bilingual_highlight:
        highlight_path = None
        highlight_keyword_path = os.path.join(normalized_dir, f"overlay_keyword_{scene_index_zero_based:03d}_0.png")
        
        # Try bilingual render first
        highlight_path = build_bilingual_highlight_image(
            highlight_keyword_path,
            bilingual_highlight,
            fonts_dir,
            highlight_spec,
        )
        
        # Fallback to legacy single-text if bilingual disabled or failed
        if highlight_path is None:
            highlight_path = build_text_overlay_image(
                highlight_keyword_path,
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
