from __future__ import annotations

import argparse
import math
import os
import sys
from pathlib import Path
from typing import Iterable, Tuple

from PIL import Image, ImageDraw, ImageFilter, ImageFont


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.overlay_style_engine import STYLE_PRESETS, get_overlay_style
from modules.style_content_link import apply_style_content_link
from modules.prompt_generator import generate_by_prompt
from modules.style_selector import select_style


OUTPUT_DIR = PROJECT_ROOT / "output" / "frame_preview"
CANVAS_SIZE = (1080, 1350)
STYLE_ORDER = [
    "creator_clean",
    "product_focus",
    "life_story",
    "ai_control_lab",
    "personal_ip",
]
DEFAULT_TITLE = "真正的问题，不是你不够努力"
DEFAULT_HIGHLIGHT = "而是你一直在用错误的方法"


def _font_candidates(style_name: str, bold: bool = False) -> list[str]:
    fonts_dir = PROJECT_ROOT / "fonts"
    if style_name == "ai_control_lab":
        return [
            "C:/Windows/Fonts/msyhbd.ttc",
            "C:/Windows/Fonts/msyh.ttc",
            str(fonts_dir / "SourceHanSansCN-Bold.otf"),
            str(fonts_dir / "SourceHanSansSC-Regular.otf"),
            "C:/Windows/Fonts/consolab.ttf",
            "C:/Windows/Fonts/consola.ttf",
            "C:/Windows/Fonts/lucon.ttf",
        ]
    if style_name == "product_focus":
        return [
            "C:/Windows/Fonts/msyhbd.ttc",
            str(fonts_dir / "SourceHanSansCN-Bold.otf"),
            "C:/Windows/Fonts/bahnschrift.ttf",
            "C:/Windows/Fonts/arialbd.ttf",
        ]
    if style_name == "life_story":
        return [
            str(fonts_dir / "SourceHanSansSC-Regular.otf"),
            "C:/Windows/Fonts/msyh.ttc",
            "C:/Windows/Fonts/simsun.ttc",
            "C:/Windows/Fonts/seguisb.ttf",
        ]
    if style_name == "personal_ip":
        return [
            "C:/Windows/Fonts/msyhbd.ttc",
            str(fonts_dir / "SourceHanSansCN-Bold.otf"),
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/segoeuib.ttf",
        ]
    return [
        "C:/Windows/Fonts/msyh.ttc",
        str(fonts_dir / "SourceHanSansSC-Regular.otf"),
        "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]


def _load_font(style_name: str, size: int, bold: bool = False):
    for candidate in _font_candidates(style_name, bold=bold):
        if candidate and os.path.exists(candidate):
            try:
                return ImageFont.truetype(candidate, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _add_alpha(color: Tuple[int, int, int, int] | Tuple[int, int, int], alpha: int) -> Tuple[int, int, int, int]:
    if len(color) == 4:
        return (int(color[0]), int(color[1]), int(color[2]), alpha)
    return (int(color[0]), int(color[1]), int(color[2]), alpha)


def _blend(left: Tuple[int, int, int, int], right: Tuple[int, int, int, int], ratio: float) -> Tuple[int, int, int, int]:
    amount = max(0.0, min(1.0, ratio))
    return tuple(int(left[index] * (1.0 - amount) + right[index] * amount) for index in range(4))


def _lighten(color: Tuple[int, int, int, int], amount: float) -> Tuple[int, int, int, int]:
    return tuple(int(channel + (255 - channel) * amount) if index < 3 else channel for index, channel in enumerate(color))


def _darken(color: Tuple[int, int, int, int], amount: float) -> Tuple[int, int, int, int]:
    return tuple(int(channel * (1.0 - amount)) if index < 3 else channel for index, channel in enumerate(color))


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    results: list[str] = []
    current = ""
    for char in str(text or ""):
        candidate = current + char
        box = draw.textbbox((0, 0), candidate, font=font, stroke_width=2)
        width = box[2] - box[0]
        if current and width > max_width:
            results.append(current)
            current = char
        else:
            current = candidate
    if current:
        results.append(current)
    return results or [""]


def _measure_multiline(draw: ImageDraw.ImageDraw, lines: Iterable[str], font, line_gap: int) -> Tuple[int, int]:
    width = 0
    height = 0
    normalized_lines = list(lines)
    for index, line in enumerate(normalized_lines):
        bbox = draw.textbbox((0, 0), line, font=font, stroke_width=2)
        width = max(width, bbox[2] - bbox[0])
        height += bbox[3] - bbox[1]
        if index < len(normalized_lines) - 1:
            height += line_gap
    return width, height


def _measure_text(draw: ImageDraw.ImageDraw, text: str, font) -> Tuple[int, int]:
    bbox = draw.textbbox((0, 0), text, font=font, stroke_width=2)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _resolve_horizontal_layout(style_name: str, position_mode: str, max_width: int) -> Tuple[int, str]:
    width = CANVAS_SIZE[0]
    mode = str(position_mode or "").lower()
    if "left" in mode or "poster" in mode or style_name == "product_focus":
        return 72, "left"
    if "impact" in mode or style_name == "personal_ip":
        return width // 2 + 42, "center"
    if "hud" in mode:
        return 64, "left"
    return width // 2, "center"


def _resolve_vertical_y(kind: str, spec: dict) -> int:
    if kind == "title":
        return int(spec.get("position_y", 96) or 96)
    return max(40, int(CANVAS_SIZE[1] * float(spec.get("position_ratio_y", 0.42) or 0.42)))


def _draw_background(style_name: str, image: Image.Image, title_spec: dict, highlight_spec: dict) -> None:
    draw = ImageDraw.Draw(image, "RGBA")
    width, height = image.size
    title_bg = tuple(title_spec.get("bg_color", (20, 20, 20, 180)))
    highlight_bg = tuple(highlight_spec.get("bg_color", (30, 30, 30, 210)))
    base_top = _darken(_blend(title_bg, highlight_bg, 0.35), 0.18)
    base_bottom = _lighten(_blend(title_bg, highlight_bg, 0.55), 0.06)

    for y in range(height):
        ratio = y / max(1, height - 1)
        color = _blend(base_top, base_bottom, ratio)
        draw.line([(0, y), (width, y)], fill=color, width=1)

    if style_name == "creator_clean":
        for y in range(180, height, 120):
            draw.line([(110, y), (width - 110, y)], fill=_add_alpha((255, 255, 255), 18), width=1)
        draw.rounded_rectangle([(80, 80), (width - 80, height - 80)], radius=36, outline=_add_alpha((255, 255, 255), 24), width=2)
    elif style_name == "product_focus":
        for index in range(-2, 5):
            offset = index * 180
            draw.polygon(
                [(offset, height), (offset + 180, height), (offset + 520, 0), (offset + 340, 0)],
                fill=_add_alpha((255, 149, 0), 34 if index % 2 == 0 else 18),
            )
        draw.rectangle([(0, height - 210), (width, height)], fill=_add_alpha((0, 20, 60), 120))
    elif style_name == "life_story":
        glow = Image.new("RGBA", image.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow, "RGBA")
        glow_draw.ellipse([(120, 780), (width - 120, height + 80)], fill=_add_alpha((255, 196, 140), 76))
        glow_draw.ellipse([(240, 180), (width - 200, 740)], fill=_add_alpha((255, 232, 214), 34))
        image.alpha_composite(glow.filter(ImageFilter.GaussianBlur(26)))
    elif style_name == "ai_control_lab":
        for x in range(0, width, 72):
            draw.line([(x, 0), (x, height)], fill=_add_alpha((80, 220, 255), 24), width=1)
        for y in range(0, height, 72):
            draw.line([(0, y), (width, y)], fill=_add_alpha((80, 220, 255), 18), width=1)
        draw.rectangle([(32, 32), (width - 32, height - 32)], outline=_add_alpha((90, 255, 245), 70), width=2)
    elif style_name == "personal_ip":
        draw.rectangle([(0, 0), (width, height)], fill=_add_alpha((255, 255, 255), 8))
        draw.polygon([(0, 0), (width * 0.65, 0), (width * 0.32, height), (0, height)], fill=_add_alpha((255, 214, 10), 42))
        draw.rectangle([(36, 36), (width - 36, height - 36)], outline=_add_alpha((255, 255, 255), 90), width=4)


def _split_bilingual_text(bilingual_text: str) -> tuple[str, str]:
    """Extract zh and en from bilingual text."""
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


def _draw_card(image: Image.Image, text: str, spec: dict, style_name: str, kind: str) -> None:
    """
    Draw a card (single-text mode, legacy).
    Used when bilingual mode is disabled or bilingual rendering fails.
    """
    width, _ = image.size
    font_size = int(spec.get("font_size", 48) or 48)
    max_width = int(spec.get("max_width", 760) or 760)
    padding_x = int(spec.get("padding_x", 28) or 28)
    padding_y = int(spec.get("padding_y", 20) or 20)
    radius = int(spec.get("radius", 24) or 24)
    bg_color = tuple(spec.get("bg_color", (20, 20, 20, 200)))
    text_color = tuple(spec.get("text_color", (255, 255, 255, 255)))
    font = _load_font(style_name, font_size, bold=style_name in {"product_focus", "personal_ip"} or kind == "highlight")
    draft = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draft_draw = ImageDraw.Draw(draft)
    wrapped = _wrap_text(draft_draw, text, font, max_width - padding_x * 2)
    line_gap = max(10, int(font_size * 0.18))
    text_width, text_height = _measure_multiline(draft_draw, wrapped, font, line_gap)

    card_width = min(max_width, text_width + padding_x * 2)
    card_height = text_height + padding_y * 2
    x_anchor, align = _resolve_horizontal_layout(style_name, str(spec.get("position_mode", "")), card_width)
    y = _resolve_vertical_y(kind, spec)

    if align == "left":
        x = max(24, min(x_anchor, width - card_width - 24))
    else:
        x = max(24, min(int(x_anchor - card_width / 2), width - card_width - 24))

    layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    layer_draw = ImageDraw.Draw(layer, "RGBA")
    shadow_alpha = 54 if spec.get("fade_enabled", True) else 88
    shadow_offset = 18 if kind == "highlight" else 12
    layer_draw.rounded_rectangle(
        [(x + shadow_offset, y + shadow_offset), (x + card_width + shadow_offset, y + card_height + shadow_offset)],
        radius=max(2, radius),
        fill=_add_alpha((0, 0, 0), shadow_alpha),
    )
    layer = layer.filter(ImageFilter.GaussianBlur(10 if kind == "highlight" else 6))
    image.alpha_composite(layer)

    card_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
    card_draw = ImageDraw.Draw(card_layer, "RGBA")
    card_draw.rounded_rectangle([(x, y), (x + card_width, y + card_height)], radius=max(2, radius), fill=bg_color)

    if style_name == "product_focus" and kind == "highlight":
        card_draw.rectangle([(x, y), (x + 18, y + card_height)], fill=_add_alpha((255, 149, 0), 255))
    if style_name == "ai_control_lab":
        card_draw.rectangle([(x, y), (x + card_width, y + 4)], fill=_add_alpha((86, 255, 240), 255))
        card_draw.rectangle([(x, y + card_height - 4), (x + card_width, y + card_height)], fill=_add_alpha((86, 255, 240), 180))
    if style_name == "personal_ip" and kind == "highlight":
        card_draw.rectangle([(x, y), (x + card_width, y + card_height)], outline=_add_alpha((12, 12, 12), 255), width=4)

    current_y = y + padding_y
    stroke_fill = (12, 12, 12, 190) if style_name != "personal_ip" else (255, 255, 255, 210)
    for line in wrapped:
        bbox = card_draw.textbbox((0, 0), line, font=font, stroke_width=2)
        line_width = bbox[2] - bbox[0]
        line_height = bbox[3] - bbox[1]
        if align == "left":
            text_x = x + padding_x
        else:
            text_x = x + (card_width - line_width) // 2
        card_draw.text(
            (text_x, current_y),
            line,
            font=font,
            fill=text_color,
            stroke_width=2,
            stroke_fill=stroke_fill,
        )
        current_y += line_height + line_gap
    image.alpha_composite(card_layer)


def _draw_bilingual_card(image: Image.Image, text: str, spec: dict, style_name: str, kind: str) -> bool:
    """
    V1 Bilingual card rendering: split zh/en with independent colors and sizes.
    
    Supported layouts:
    - zh_en_stacked: zh on top, en below
    - zh_en_inline: zh on left, en on right
    - zh_only: only zh
    - en_only: only en
    
    Returns True if bilingual render succeeded, False if should fallback to legacy mode.
    """
    # Check if bilingual render is enabled
    if not spec.get("bilingual_render_enabled", True):
        return False  # Signal fallback
    
    try:
        # Extract zh and en
        zh_text, en_text = _split_bilingual_text(text)
        zh_text = str(zh_text or "").strip()
        en_text = str(en_text or "").strip()
        
        # Determine layout
        layout = str(spec.get("zh_en_layout", "zh_en_stacked") or "zh_en_stacked").lower()
        
        # Handle zh_only / en_only cases
        if layout == "zh_only":
            en_text = ""
        elif layout == "en_only":
            zh_text = ""
        
        # If no text at all, fail gracefully
        if not zh_text and not en_text:
            return False
        
        width, _ = image.size
        padding_x = int(spec.get("padding_x", 28) or 28)
        padding_y = int(spec.get("padding_y", 20) or 20)
        radius = int(spec.get("radius", 24) or 24)
        bg_color = tuple(spec.get("bg_color", (20, 20, 20, 200)))
        max_width = int(spec.get("max_width", 760) or 760)
        
        # Configure colors and fonts
        zh_color = tuple(spec.get("zh_text_color", None) or spec.get("text_color", (255, 255, 255, 255)))
        en_color = tuple(spec.get("en_text_color", None) or spec.get("text_color", (255, 255, 255, 255)))
        
        zh_font_size = int(spec.get("zh_font_size", None) or spec.get("font_size", 48) or 48)
        en_font_size = int(spec.get("en_font_size", None) or spec.get("font_size", 48) or 48)
        
        gap = int(spec.get("zh_en_gap", 10) or 10)
        
        zh_font = _load_font(style_name, zh_font_size, bold=style_name in {"product_focus", "personal_ip"} or kind == "highlight")
        en_font = _load_font(style_name, en_font_size, bold=False)
        
        # Measure text blocks
        draft = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 0))
        draft_draw = ImageDraw.Draw(draft)
        
        zh_wrapped = _wrap_text(draft_draw, zh_text, zh_font, max_width - padding_x * 2) if zh_text else []
        en_wrapped = _wrap_text(draft_draw, en_text, en_font, max_width - padding_x * 2) if en_text else []
        
        # Calculate for stacked layout (default)
        if layout in ("zh_en_stacked", ""):
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
            
            x_anchor, align = _resolve_horizontal_layout(style_name, str(spec.get("position_mode", "")), card_width)
            y = _resolve_vertical_y(kind, spec)
            
            if align == "left":
                x = max(24, min(x_anchor, width - card_width - 24))
            else:
                x = max(24, min(int(x_anchor - card_width / 2), width - card_width - 24))
            
            # Shadow layer
            layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
            layer_draw = ImageDraw.Draw(layer, "RGBA")
            shadow_alpha = 54 if spec.get("fade_enabled", True) else 88
            shadow_offset = 18 if kind == "highlight" else 12
            layer_draw.rounded_rectangle(
                [(x + shadow_offset, y + shadow_offset), (x + card_width + shadow_offset, y + card_height + shadow_offset)],
                radius=max(2, radius),
                fill=_add_alpha((0, 0, 0), shadow_alpha),
            )
            layer = layer.filter(ImageFilter.GaussianBlur(10 if kind == "highlight" else 6))
            image.alpha_composite(layer)
            
            # Card layer
            card_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
            card_draw = ImageDraw.Draw(card_layer, "RGBA")
            card_draw.rounded_rectangle([(x, y), (x + card_width, y + card_height)], radius=max(2, radius), fill=bg_color)
            
            if style_name == "product_focus" and kind == "highlight":
                card_draw.rectangle([(x, y), (x + 18, y + card_height)], fill=_add_alpha((255, 149, 0), 255))
            if style_name == "ai_control_lab":
                card_draw.rectangle([(x, y), (x + card_width, y + 4)], fill=_add_alpha((86, 255, 240), 255))
                card_draw.rectangle([(x, y + card_height - 4), (x + card_width, y + card_height)], fill=_add_alpha((86, 255, 240), 180))
            if style_name == "personal_ip" and kind == "highlight":
                card_draw.rectangle([(x, y), (x + card_width, y + card_height)], outline=_add_alpha((12, 12, 12), 255), width=4)
            
            stroke_fill = (12, 12, 12, 190) if style_name != "personal_ip" else (255, 255, 255, 210)
            
            current_y = y + padding_y
            
            # Draw zh text
            for line, line_height in zip(zh_wrapped, zh_lines_heights):
                line_width, _ = _measure_text(card_draw, line, zh_font)
                if align == "left":
                    text_x = x + padding_x
                else:
                    text_x = x + (card_width - line_width) // 2
                card_draw.text(
                    (text_x, current_y),
                    line,
                    font=zh_font,
                    fill=zh_color,
                    stroke_width=2,
                    stroke_fill=stroke_fill,
                )
                current_y += line_height + line_gap
            
            # Add gap
            if zh_height > 0 and en_height > 0:
                current_y += gap - line_gap
            
            # Draw en text
            for line, line_height in zip(en_wrapped, en_lines_heights):
                line_width, _ = _measure_text(card_draw, line, en_font)
                if align == "left":
                    text_x = x + padding_x
                else:
                    text_x = x + (card_width - line_width) // 2
                card_draw.text(
                    (text_x, current_y),
                    line,
                    font=en_font,
                    fill=en_color,
                    stroke_width=2,
                    stroke_fill=stroke_fill,
                )
                current_y += line_height + line_gap
            
            image.alpha_composite(card_layer)
            return True
        
        elif layout == "zh_en_inline":
            # Inline layout: zh on left, en on right
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
            
            x_anchor, align = _resolve_horizontal_layout(style_name, str(spec.get("position_mode", "")), card_width)
            y = _resolve_vertical_y(kind, spec)
            
            if align == "left":
                x = max(24, min(x_anchor, width - card_width - 24))
            else:
                x = max(24, min(int(x_anchor - card_width / 2), width - card_width - 24))
            
            # Shadow and card layers
            layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
            layer_draw = ImageDraw.Draw(layer, "RGBA")
            shadow_alpha = 54 if spec.get("fade_enabled", True) else 88
            shadow_offset = 18 if kind == "highlight" else 12
            layer_draw.rounded_rectangle(
                [(x + shadow_offset, y + shadow_offset), (x + card_width + shadow_offset, y + card_height + shadow_offset)],
                radius=max(2, radius),
                fill=_add_alpha((0, 0, 0), shadow_alpha),
            )
            layer = layer.filter(ImageFilter.GaussianBlur(10 if kind == "highlight" else 6))
            image.alpha_composite(layer)
            
            card_layer = Image.new("RGBA", image.size, (0, 0, 0, 0))
            card_draw = ImageDraw.Draw(card_layer, "RGBA")
            card_draw.rounded_rectangle([(x, y), (x + card_width, y + card_height)], radius=max(2, radius), fill=bg_color)
            
            if style_name == "product_focus" and kind == "highlight":
                card_draw.rectangle([(x, y), (x + 18, y + card_height)], fill=_add_alpha((255, 149, 0), 255))
            if style_name == "ai_control_lab":
                card_draw.rectangle([(x, y), (x + card_width, y + 4)], fill=_add_alpha((86, 255, 240), 255))
                card_draw.rectangle([(x, y + card_height - 4), (x + card_width, y + card_height)], fill=_add_alpha((86, 255, 240), 180))
            if style_name == "personal_ip" and kind == "highlight":
                card_draw.rectangle([(x, y), (x + card_width, y + card_height)], outline=_add_alpha((12, 12, 12), 255), width=4)
            
            stroke_fill = (12, 12, 12, 190) if style_name != "personal_ip" else (255, 255, 255, 210)
            
            # Draw zh on left
            current_x = x + padding_x
            current_y = y + padding_y + (max_height - zh_height) // 2
            
            for line in zh_wrapped:
                card_draw.text(
                    (current_x, current_y),
                    line,
                    font=zh_font,
                    fill=zh_color,
                    stroke_width=2,
                    stroke_fill=stroke_fill,
                )
                line_height = _measure_text(card_draw, line, zh_font)[1]
                current_y += line_height + line_gap
            
            # Draw en on right
            current_x = x + padding_x + zh_width + (gap if zh_width > 0 and en_width > 0 else 0)
            current_y = y + padding_y + (max_height - en_height) // 2
            
            for line in en_wrapped:
                card_draw.text(
                    (current_x, current_y),
                    line,
                    font=en_font,
                    fill=en_color,
                    stroke_width=2,
                    stroke_fill=stroke_fill,
                )
                line_height = _measure_text(card_draw, line, en_font)[1]
                current_y += line_height + line_gap
            
            image.alpha_composite(card_layer)
            return True
        
        else:
            # Unknown layout
            return False
    
    except Exception as e:
        print(f"[BILINGUAL_CARD] error={e}, falling back to legacy mode")
        return False


def _draw_style_label(image: Image.Image, style_name: str) -> None:
    label_font = _load_font(style_name, 28, bold=True)
    draw = ImageDraw.Draw(image, "RGBA")
    label = f"STYLE: {style_name}"
    bbox = draw.textbbox((0, 0), label, font=label_font)
    label_width = bbox[2] - bbox[0]
    label_height = bbox[3] - bbox[1]
    x = 34
    y = CANVAS_SIZE[1] - label_height - 42
    draw.rounded_rectangle([(x - 14, y - 8), (x + label_width + 14, y + label_height + 10)], radius=12, fill=(0, 0, 0, 120))
    draw.text((x, y), label, font=label_font, fill=(255, 255, 255, 230))


def render_style_preview(style_name: str, title: str, highlight: str, output_path: Path) -> Path:
    if style_name not in STYLE_PRESETS:
        raise ValueError(f"Unknown style: {style_name}")

    style = get_overlay_style(style_name)
    final_title = title
    final_highlight = highlight

    try:
        styled_content = apply_style_content_link(style_name, title, highlight)
        final_title = str(styled_content.get("title", title) or title)
        final_highlight = str(styled_content.get("highlight", highlight) or highlight)
    except Exception:
        final_title = title
        final_highlight = highlight

    image = Image.new("RGBA", CANVAS_SIZE, (8, 10, 16, 255))
    title_spec = style.get("title", {})
    highlight_spec = style.get("highlight", {})

    _draw_background(style_name, image, title_spec, highlight_spec)
    
    # Draw title (currently single-text only)
    _draw_card(image, final_title, title_spec, style_name, kind="title")
    
    # Draw highlight with V1 bilingual support
    # Try bilingual first, fall back to legacy if disabled/failed
    bilingual_succeeded = _draw_bilingual_card(image, final_highlight, highlight_spec, style_name, kind="highlight")
    if not bilingual_succeeded:
        _draw_card(image, final_highlight, highlight_spec, style_name, kind="highlight")
    
    _draw_style_label(image, style_name)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("RGB").save(output_path, format="PNG")
    return output_path


def build_style_grid(image_paths: list[Path], output_path: Path) -> Path:
    thumb_width = 432
    thumb_height = 540
    gap = 30
    cols = 2
    rows = math.ceil(len(image_paths) / cols)
    grid_width = thumb_width * cols + gap * (cols + 1)
    grid_height = thumb_height * rows + gap * (rows + 1)
    grid = Image.new("RGB", (grid_width, grid_height), (18, 20, 26))
    draw = ImageDraw.Draw(grid)
    label_font = _load_font("creator_clean", 24, bold=True)

    for index, path in enumerate(image_paths):
        row = index // cols
        col = index % cols
        x = gap + col * (thumb_width + gap)
        y = gap + row * (thumb_height + gap)
        preview = Image.open(path).convert("RGB")
        preview.thumbnail((thumb_width, thumb_height))
        offset_x = x + (thumb_width - preview.width) // 2
        offset_y = y + (thumb_height - preview.height) // 2
        draw.rounded_rectangle([(x, y), (x + thumb_width, y + thumb_height)], radius=20, fill=(28, 30, 38), outline=(64, 68, 80), width=2)
        grid.paste(preview, (offset_x, offset_y))
        label = path.stem.replace("preview_", "")
        draw.text((x + 18, y + 18), label, font=label_font, fill=(245, 246, 248))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    grid.save(output_path, format="PNG")
    return output_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render static frame previews for overlay styles (V1 bilingual + auto-style support).")
    parser.add_argument("--style", choices=STYLE_ORDER, default=None, help="Manually specify a style (highest priority); if set, auto-style is ignored.")
    parser.add_argument("--auto-style", action="store_true", default=False, help="Enable auto style selection based on input text (only used if --style is not specified).")
    parser.add_argument("--title", default=None, help="Title text. If None, uses AI (if enabled) or defaults.")
    parser.add_argument("--highlight", default=None, help="Highlight text. If None, uses AI (if enabled) or defaults.")
    parser.add_argument("--input-text", default="示例输入内容", help="Input text for auto style selection and AI generation.")
    parser.add_argument("--disable-ai", action="store_true", default=False, help="Disable AI content generation (use defaults instead).")
    return parser.parse_args()


def _mock_ai_call(prompt: str) -> str:
    """Mock AI调用函数。生产环境可替换为真实模型。"""
    return "Title: 真正的问题，不是你不够努力\nHighlight: 而是你一直在用错误的方法"


def process_single_item(
    input_text: str,
    style_name: str | None = None,
    title: str | None = None,
    highlight: str | None = None,
    enable_ai: bool = True,
) -> dict:
    """
    处理单条item的核心逻辑（可复用于批量生成）
    
    返回: {
        "style_name": "...",
        "title": "...",
        "highlight": "...",
        "used_auto_style": bool,
        "used_ai_generation": bool,
    }
    """
    # 第1层：style选择
    used_auto_style = False
    if style_name:
        # 🥇 人工指定style
        final_style = style_name
    else:
        # 🥈 自动选style
        final_style = select_style(input_text)
        used_auto_style = True
    
    # 第2层：内容生成
    used_ai_generation = False
    final_title = title
    final_highlight = highlight
    
    if (not final_title or not final_highlight) and enable_ai:
        # 🥈 AI生成
        ai_result = generate_by_prompt(
            input_text=input_text,
            style_name=final_style,
            call_ai_func=_mock_ai_call
        )
        if ai_result:
            if not final_title:
                final_title = ai_result.get("title")
            if not final_highlight:
                final_highlight = ai_result.get("highlight")
            used_ai_generation = True
    
    # 🥉 回退到默认值
    final_title = final_title or DEFAULT_TITLE
    final_highlight = final_highlight or DEFAULT_HIGHLIGHT
    
    # 第3层：style_content_link轻修正
    try:
        styled_content = apply_style_content_link(final_style, final_title, final_highlight)
        final_title = str(styled_content.get("title", final_title) or final_title)
        final_highlight = str(styled_content.get("highlight", final_highlight) or final_highlight)
    except Exception:
        pass  # 修正失败则保持原值
    
    return {
        "style_name": final_style,
        "title": final_title,
        "highlight": final_highlight,
        "used_auto_style": used_auto_style,
        "used_ai_generation": used_ai_generation,
    }


def main() -> None:
    args = parse_args()
    
    # 优先级规则：人工指定style > 自动选style > 默认style
    if args.style:
        # 🥇 优先级1：人工指定style
        selected_styles = [args.style]
        print(f"[FRAME_PREVIEW] Using manually specified style: {args.style}")
    elif args.auto_style:
        # 🥈 优先级2：自动选style
        selected_style = select_style(args.input_text)
        selected_styles = [selected_style]
        print(f"[FRAME_PREVIEW] Auto-selected style: {selected_style} (input: {args.input_text[:30]}...)")
    else:
        # 🥉 优先级3：默认行为（渲染所有style）
        selected_styles = list(STYLE_ORDER)
        print(f"[FRAME_PREVIEW] No style specified; rendering all styles")
    
    generated_paths: list[Path] = []
    
    # AI开关和参数
    ENABLE_AI = not args.disable_ai
    input_text = args.input_text

    for style_name in selected_styles:
        # 初始化标题和高亮
        title = args.title
        highlight = args.highlight
        
        # 优先级：人工输入 > AI生成 > 默认值
        if not title or not highlight:
            if ENABLE_AI:
                print(f"[FRAME_PREVIEW] Generating content for style={style_name}...")
                ai_result = generate_by_prompt(
                    input_text=input_text,
                    style_name=style_name,
                    call_ai_func=_mock_ai_call
                )
                if ai_result:
                    if not title:
                        title = ai_result.get("title")
                        print(f"  [AI] title={title}")
                    if not highlight:
                        highlight = ai_result.get("highlight")
                        print(f"  [AI] highlight={highlight}")
        
        # 回退到默认值
        title = title or DEFAULT_TITLE
        highlight = highlight or DEFAULT_HIGHLIGHT
        
        output_path = OUTPUT_DIR / f"preview_{style_name}.png"
        render_style_preview(style_name, title, highlight, output_path)
        generated_paths.append(output_path)
        print(f"[FRAME_PREVIEW] generated={output_path.relative_to(PROJECT_ROOT)}")

    if not args.style:
        grid_path = OUTPUT_DIR / "style_grid.png"
        build_style_grid(generated_paths, grid_path)
        print(f"[FRAME_PREVIEW] generated={grid_path.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
