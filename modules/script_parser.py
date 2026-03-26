import os
import textwrap
from typing import List, Dict, Any

from PIL import Image, ImageDraw, ImageFont

WIDTH = 1080
HEIGHT = 1920

TITLE_RATIO = 0.15
IMAGE_RATIO = 0.70
CAPTION_RATIO = 0.15

TITLE_HEIGHT = int(HEIGHT * TITLE_RATIO)
IMAGE_HEIGHT = int(HEIGHT * IMAGE_RATIO)
CAPTION_HEIGHT = HEIGHT - TITLE_HEIGHT - IMAGE_HEIGHT


def get_font(size: int):
    font_candidates = [
        "msyh.ttc",          # 微软雅黑
        "simhei.ttf",        # 黑体
        "simsun.ttc",        # 宋体
        "arial.ttf",         # Arial
    ]
    for font_name in font_candidates:
        try:
            return ImageFont.truetype(font_name, size)
        except Exception:
            continue
    return ImageFont.load_default()


def wrap_text(text: str, width: int) -> str:
    if not text:
        return ""
    return "\n".join(textwrap.wrap(text, width=width))


def draw_multiline_centered(
    draw: ImageDraw.ImageDraw,
    box: tuple,
    text: str,
    font,
    fill=(0, 0, 0),
    spacing: int = 12
) -> None:
    left, top, right, bottom = box
    box_w = right - left
    box_h = bottom - top

    lines = text.split("\n")
    line_heights = []
    line_widths = []

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        h = bbox[3] - bbox[1]
        line_widths.append(w)
        line_heights.append(h)

    total_h = sum(line_heights) + spacing * (len(lines) - 1)
    y = top + (box_h - total_h) / 2

    for i, line in enumerate(lines):
        w = line_widths[i]
        h = line_heights[i]
        x = left + (box_w - w) / 2
        draw.text((x, y), line, font=font, fill=fill)
        y += h + spacing


def render_cards(cards: List[Dict[str, Any]], output_dir: str) -> List[str]:
    card_paths: List[str] = []

    title_font = get_font(64)
    image_font = get_font(80)
    caption_font = get_font(50)
    small_font = get_font(36)

    for idx, card in enumerate(cards, start=1):
        img = Image.new("RGB", (WIDTH, HEIGHT), (255, 255, 255))
        draw = ImageDraw.Draw(img)

        # 标题区
        draw.rectangle(
            [(0, 0), (WIDTH, TITLE_HEIGHT)],
            fill=(245, 245, 245)
        )

        title_text = wrap_text(str(card["title"]), width=14)
        draw_multiline_centered(
            draw,
            (40, 20, WIDTH - 40, TITLE_HEIGHT - 20),
            title_text,
            title_font,
            fill=(20, 20, 20),
            spacing=10
        )

        # 图片区占位
        image_top = TITLE_HEIGHT
        image_bottom = TITLE_HEIGHT + IMAGE_HEIGHT

        draw.rectangle(
            [(60, image_top + 40), (WIDTH - 60, image_bottom - 40)],
            fill=(220, 220, 220),
            outline=(180, 180, 180),
            width=4
        )

        draw_multiline_centered(
            draw,
            (80, image_top + 80, WIDTH - 80, image_bottom - 80),
            "IMAGE\nPLACEHOLDER",
            image_font,
            fill=(90, 90, 90),
            spacing=20
        )

        draw_multiline_centered(
            draw,
            (80, image_bottom - 180, WIDTH - 80, image_bottom - 60),
            f"Card {idx}",
            small_font,
            fill=(120, 120, 120),
            spacing=10
        )

        # 说明区
        caption_top = image_bottom
        draw.rectangle(
            [(0, caption_top), (WIDTH, HEIGHT)],
            fill=(245, 245, 245)
        )

        caption_text = wrap_text(str(card["caption"]), width=18)
        draw_multiline_centered(
            draw,
            (40, caption_top + 20, WIDTH - 40, HEIGHT - 20),
            caption_text,
            caption_font,
            fill=(20, 20, 20),
            spacing=12
        )

        card_path = os.path.join(output_dir, f"card_{idx}.png")
        img.save(card_path)
        card_paths.append(card_path)

    return card_paths