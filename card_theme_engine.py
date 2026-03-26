# -*- coding: utf-8 -*-
"""
card_theme_engine.py
========================================================
作用：
1. 根据 card 内容 + theme_config.json 渲染图卡
2. 兼容旧调用方式：render_card(card, width, height, total_cards)
3. 支持 theme_config.json 中的 themes 切换能力
4. 保留旧结构：
   - theme_name
   - overlay
   - card
   - text
   - brand
5. 新增支持：
   - themes[theme_name] 对默认 overlay/text 做覆盖

说明：
- 这个版本优先兼容你当前工程，不做激进重构
- 用户主要通过 theme_config.json + project_config.json 控制风格
"""

import os
import re
import json
from typing import Dict, Any, Tuple, List, Optional

from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter

DEFAULT_OUTPUT_DIR = "output"
DEFAULT_THEME_CONFIG_PATH = "theme_config.json"
DEFAULT_CANVAS_WIDTH = 1080
DEFAULT_CANVAS_HEIGHT = 1920


# =========================================================
# 基础工具
# =========================================================

def safe_read_json(path: str, default: Any) -> Any:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    result = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = v
    return result


def normalize_text(text: Any) -> str:
    if text is None:
        return ""
    text = str(text)
    text = text.replace("\u3000", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def truncate_text(text: str, max_chars: int) -> str:
    text = normalize_text(text)
    if len(text) <= max_chars:
        return text
    if max_chars <= 1:
        return text[:max_chars]
    return text[:max_chars - 1].rstrip() + "…"


# =========================================================
# 读取 theme_config，并支持 themes 覆盖
# =========================================================

def load_theme_config(theme_config_path: str = DEFAULT_THEME_CONFIG_PATH) -> Dict[str, Any]:
    """
    读取 theme_config.json
    支持：
    - 顶层默认配置
    - themes[theme_name] 覆盖 overlay / text / 以后可扩展更多
    """
    default_cfg = {
        "theme_name": "editorial_cover",
        "show_page_number": True,
        "show_brand": False,
        "overlay": {
            "height_ratio": 0.38,
            "opacity": 175,
            "color": [0, 0, 0]
        },
        "card": {
            "corner_radius": 36,
            "padding_x": 60,
            "padding_bottom": 56
        },
        "text": {
            "title_size": 62,
            "subtitle_size": 34,
            "body_size": 24,
            "title_color": [255, 255, 255],
            "subtitle_color": [228, 228, 228],
            "body_color": [190, 190, 190],
            "page_color": [220, 220, 220],
            "brand_color": [150, 150, 150]
        },
        "brand": {
            "channel_name": "Geoff Knowledge"
        },
        "themes": {}
    }

    user_cfg = safe_read_json(theme_config_path, {})
    if not isinstance(user_cfg, dict):
        user_cfg = {}

    cfg = deep_merge(default_cfg, user_cfg)

    theme_name = cfg.get("theme_name", "editorial_cover")
    themes = cfg.get("themes", {})

    if isinstance(themes, dict) and theme_name in themes and isinstance(themes[theme_name], dict):
        theme_override = themes[theme_name]

        # 只覆盖已经存在的结构层，避免破坏原逻辑
        if "overlay" in theme_override and isinstance(theme_override["overlay"], dict):
            cfg["overlay"] = deep_merge(cfg.get("overlay", {}), theme_override["overlay"])

        if "text" in theme_override and isinstance(theme_override["text"], dict):
            cfg["text"] = deep_merge(cfg.get("text", {}), theme_override["text"])

        if "card" in theme_override and isinstance(theme_override["card"], dict):
            cfg["card"] = deep_merge(cfg.get("card", {}), theme_override["card"])

        if "brand" in theme_override and isinstance(theme_override["brand"], dict):
            cfg["brand"] = deep_merge(cfg.get("brand", {}), theme_override["brand"])

    return cfg


# =========================================================
# 字体
# =========================================================

def get_font_candidates() -> List[str]:
    return [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "fonts/msyh.ttc",
        "fonts/msyhbd.ttc",
        "fonts/simhei.ttf",
        "fonts/arial.ttf",
        "fonts/arialbd.ttf",
    ]


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = get_font_candidates()

    if bold:
        bold_first = []
        normal_rest = []
        for p in candidates:
            lp = p.lower()
            if "bd" in lp or "bold" in lp:
                bold_first.append(p)
            else:
                normal_rest.append(p)
        candidates = bold_first + normal_rest

    for font_path in candidates:
        if os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size=size)
            except Exception:
                continue

    return ImageFont.load_default()


# =========================================================
# 图片工具
# =========================================================

def open_image_safe(image_path: str) -> Image.Image:
    return Image.open(image_path).convert("RGBA")


def crop_to_fill(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_w, src_h = img.size
    target_ratio = target_w / target_h
    src_ratio = src_w / src_h

    if src_ratio > target_ratio:
        new_w = int(src_h * target_ratio)
        left = (src_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, src_h))
    else:
        new_h = int(src_w / target_ratio)
        top = (src_h - new_h) // 2
        img = img.crop((0, top, src_w, top + new_h))

    return img.resize((target_w, target_h), Image.LANCZOS)


# =========================================================
# 文字排版
# =========================================================

def text_bbox(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont) -> Tuple[int, int]:
    if not text:
        return 0, 0
    box = draw.textbbox((0, 0), text, font=font)
    return box[2] - box[0], box[3] - box[1]


def wrap_text_by_width(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    max_width: int,
    max_lines: int
) -> List[str]:
    text = normalize_text(text)
    if not text:
        return []

    lines = []
    current = ""

    for ch in text:
        test = current + ch
        w, _ = text_bbox(draw, test, font)
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
                current = ch
            else:
                lines.append(ch)
                current = ""

        if len(lines) >= max_lines:
            break

    if len(lines) < max_lines and current:
        lines.append(current)

    rendered_text = "".join(lines)
    if len(rendered_text) < len(text) and lines:
        last = lines[-1]
        while True:
            if not last:
                last = "…"
                break
            candidate = last + "…"
            w, _ = text_bbox(draw, candidate, font)
            if w <= max_width:
                last = candidate
                break
            last = last[:-1]
        lines[-1] = last

    return lines


def draw_multiline_text(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    lines: List[str],
    font: ImageFont.FreeTypeFont,
    fill: Tuple[int, int, int],
    line_spacing: int
) -> int:
    current_y = y
    for line in lines:
        draw.text((x, current_y), line, font=font, fill=fill)
        _, h = text_bbox(draw, line, font)
        current_y += h + line_spacing
    return current_y


# =========================================================
# 内容提取
# =========================================================

def extract_card_text(card: Dict[str, Any]) -> Dict[str, str]:
    title = normalize_text(card.get("title", ""))
    subtitle = normalize_text(card.get("subtitle", ""))
    body = normalize_text(card.get("body", ""))
    text = normalize_text(card.get("text", ""))
    voiceover = normalize_text(card.get("voiceover", ""))

    if not body and text:
        body = text
    if not body and voiceover:
        body = voiceover

    return {
        "title": title,
        "subtitle": subtitle,
        "body": body
    }


# =========================================================
# 遮罩
# =========================================================

def build_bottom_overlay(
    width: int,
    height: int,
    color: List[int],
    opacity: int,
    height_ratio: float
) -> Image.Image:
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    h = int(height * height_ratio)
    y0 = height - h
    draw.rectangle([0, y0, width, height], fill=tuple(color) + (opacity,))
    return overlay


# =========================================================
# 内部渲染核心
# =========================================================

def _render_card_internal(
    card: Dict[str, Any],
    background_image_path: Optional[str] = None,
    output_path: Optional[str] = None,
    card_index: int = 1,
    total_cards: int = 1,
    theme_config_path: str = DEFAULT_THEME_CONFIG_PATH,
    canvas_width: Optional[int] = None,
    canvas_height: Optional[int] = None
) -> str:
    cfg = load_theme_config(theme_config_path)

    width = int(canvas_width or DEFAULT_CANVAS_WIDTH)
    height = int(canvas_height or DEFAULT_CANVAS_HEIGHT)

    os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)

    # 读取配置
    theme_name = cfg.get("theme_name", "editorial_cover")
    show_page_number = bool(cfg.get("show_page_number", True))
    show_brand = bool(cfg.get("show_brand", False))

    overlay_cfg = cfg.get("overlay", {})
    card_cfg = cfg.get("card", {})
    text_cfg = cfg.get("text", {})
    brand_cfg = cfg.get("brand", {})

    overlay_height_ratio = float(overlay_cfg.get("height_ratio", 0.38))
    overlay_opacity = int(overlay_cfg.get("opacity", 175))
    overlay_color = overlay_cfg.get("color", [0, 0, 0])

    padding_x = int(card_cfg.get("padding_x", 60))
    padding_bottom = int(card_cfg.get("padding_bottom", 56))

    title_size = int(text_cfg.get("title_size", 62))
    subtitle_size = int(text_cfg.get("subtitle_size", 34))
    body_size = int(text_cfg.get("body_size", 24))

    title_color = tuple(text_cfg.get("title_color", [255, 255, 255]))
    subtitle_color = tuple(text_cfg.get("subtitle_color", [228, 228, 228]))
    body_color = tuple(text_cfg.get("body_color", [190, 190, 190]))
    page_color = tuple(text_cfg.get("page_color", [220, 220, 220]))
    brand_color = tuple(text_cfg.get("brand_color", [150, 150, 150]))

    brand_name = normalize_text(brand_cfg.get("channel_name", "Geoff Knowledge"))

    # 读取文字
    text_map = extract_card_text(card)
    title = truncate_text(text_map["title"], 90)
    subtitle = truncate_text(text_map["subtitle"], 130)
    body = truncate_text(text_map["body"], 280)

    # 背景图
    if background_image_path and isinstance(background_image_path, str) and os.path.exists(background_image_path):
        bg = open_image_safe(background_image_path)
        bg = crop_to_fill(bg, width, height)
    else:
        # 默认纯黑背景
        bg = Image.new("RGBA", (width, height), (0, 0, 0, 255))

    # 底部遮罩
    overlay = build_bottom_overlay(
        width=width,
        height=height,
        color=overlay_color,
        opacity=overlay_opacity,
        height_ratio=overlay_height_ratio
    )
    bg = Image.alpha_composite(bg, overlay)

    draw = ImageDraw.Draw(bg)

    # 字体
    title_font = load_font(title_size, bold=True)
    subtitle_font = load_font(subtitle_size, bold=False)
    body_font = load_font(body_size, bold=False)
    page_font = load_font(24, bold=False)
    brand_font = load_font(22, bold=False)

    # 文本宽度区域
    content_x = padding_x
    content_w = width - padding_x * 2

    # 预设不同 theme 的起始位置逻辑
    if theme_name == "minimal_dark":
        start_y = int(height * 0.56)
    elif theme_name == "finance_blue":
        start_y = int(height * 0.60)
    else:
        # editorial_cover / 默认
        start_y = int(height * 0.62)

    title_lines = wrap_text_by_width(draw, title, title_font, content_w, 3)
    subtitle_lines = wrap_text_by_width(draw, subtitle, subtitle_font, content_w, 3)
    body_lines = wrap_text_by_width(draw, body, body_font, content_w, 8)

    current_y = start_y

    # title
    if title_lines:
        current_y = draw_multiline_text(
            draw=draw,
            x=content_x,
            y=current_y,
            lines=title_lines,
            font=title_font,
            fill=title_color,
            line_spacing=16
        )
        current_y += 14

    # subtitle
    if subtitle_lines:
        current_y = draw_multiline_text(
            draw=draw,
            x=content_x,
            y=current_y,
            lines=subtitle_lines,
            font=subtitle_font,
            fill=subtitle_color,
            line_spacing=10
        )
        current_y += 20

    # body
    if body_lines:
        # editorial_cover 正文更少一些
        if theme_name == "editorial_cover" and len(body_lines) > 5:
            body_lines = body_lines[:5]

        current_y = draw_multiline_text(
            draw=draw,
            x=content_x,
            y=current_y,
            lines=body_lines,
            font=body_font,
            fill=body_color,
            line_spacing=10
        )

    # 页码
    if show_page_number:
        page_text = f"{card_index:02d} / {total_cards:02d}"
        page_w, page_h = text_bbox(draw, page_text, page_font)
        page_x = width - padding_x - page_w
        page_y = height - padding_bottom - page_h
        draw.text((page_x, page_y), page_text, font=page_font, fill=page_color)

    # 品牌
    if show_brand and brand_name:
        brand_x = padding_x
        brand_y = height - padding_bottom - 28
        draw.text((brand_x, brand_y), brand_name, font=brand_font, fill=brand_color)

    # 输出路径
    if not output_path:
        output_path = os.path.join(DEFAULT_OUTPUT_DIR, f"card_{card_index}.png")

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    bg.save(output_path, format="PNG")
    return output_path


# =========================================================
# 对外主接口：兼容旧调用
# =========================================================

def render_card(card: Dict[str, Any], *args, **kwargs) -> str:
    """
    兼容两种调用：

    旧调用：
        render_card(card, width, height, total_cards)

    新调用：
        render_card(
            card=card,
            background_image_path=...,
            output_path=...,
            card_index=...,
            total_cards=...,
            theme_config_path=...,
            canvas_width=...,
            canvas_height=...
        )
    """
    # 旧调用分支
    if len(args) >= 3 and all(isinstance(x, int) for x in args[:3]):
        width = args[0]
        height = args[1]
        total_cards = args[2]

        card_index = int(card.get("_card_index", 1))
        background_image_path = card.get("_background_image_path")
        output_path = os.path.join(DEFAULT_OUTPUT_DIR, f"card_{card_index}.png")

        return _render_card_internal(
            card=card,
            background_image_path=background_image_path,
            output_path=output_path,
            card_index=card_index,
            total_cards=total_cards,
            theme_config_path=kwargs.get("theme_config_path", DEFAULT_THEME_CONFIG_PATH),
            canvas_width=width,
            canvas_height=height
        )

    # 新调用分支
    return _render_card_internal(
        card=card,
        background_image_path=kwargs.get("background_image_path"),
        output_path=kwargs.get("output_path"),
        card_index=kwargs.get("card_index", 1),
        total_cards=kwargs.get("total_cards", 1),
        theme_config_path=kwargs.get("theme_config_path", DEFAULT_THEME_CONFIG_PATH),
        canvas_width=kwargs.get("canvas_width"),
        canvas_height=kwargs.get("canvas_height")
    )


# =========================================================
# 批量渲染
# =========================================================

def render_cards(
    cards: List[Dict[str, Any]],
    background_image_paths: Optional[List[str]] = None,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    theme_config_path: str = DEFAULT_THEME_CONFIG_PATH,
    canvas_width: Optional[int] = None,
    canvas_height: Optional[int] = None
) -> List[str]:
    os.makedirs(output_dir, exist_ok=True)

    if background_image_paths is None:
        background_image_paths = [None] * len(cards)

    output_paths = []
    total_cards = len(cards)

    for idx, card in enumerate(cards, start=1):
        bg_path = background_image_paths[idx - 1] if idx - 1 < len(background_image_paths) else None
        out_path = os.path.join(output_dir, f"card_{idx}.png")

        final_path = _render_card_internal(
            card=card,
            background_image_path=bg_path,
            output_path=out_path,
            card_index=idx,
            total_cards=total_cards,
            theme_config_path=theme_config_path,
            canvas_width=canvas_width,
            canvas_height=canvas_height
        )
        output_paths.append(final_path)

    return output_paths


# =========================================================
# 兼容旧接口别名
# =========================================================

def create_card_image(
    card: Dict[str, Any],
    image_path: Optional[str] = None,
    output_path: Optional[str] = None,
    card_index: int = 1,
    total_cards: int = 1,
    theme_config_path: str = DEFAULT_THEME_CONFIG_PATH
) -> str:
    return _render_card_internal(
        card=card,
        background_image_path=image_path,
        output_path=output_path,
        card_index=card_index,
        total_cards=total_cards,
        theme_config_path=theme_config_path
    )


def render_card_image(
    card: Dict[str, Any],
    image_path: Optional[str] = None,
    output_path: Optional[str] = None,
    card_index: int = 1,
    total_cards: int = 1,
    theme_config_path: str = DEFAULT_THEME_CONFIG_PATH
) -> str:
    return create_card_image(card, image_path, output_path, card_index, total_cards, theme_config_path)


def make_card_image(
    card: Dict[str, Any],
    image_path: Optional[str] = None,
    output_path: Optional[str] = None,
    card_index: int = 1,
    total_cards: int = 1,
    theme_config_path: str = DEFAULT_THEME_CONFIG_PATH
) -> str:
    return create_card_image(card, image_path, output_path, card_index, total_cards, theme_config_path)


# =========================================================
# 自测
# =========================================================

if __name__ == "__main__":
    sample_card = {
        "title": "利率为什么会改变资产估值",
        "subtitle": "从时间价格到折现逻辑",
        "body": "当利率变化时，未来现金流的折现值也会变化，因此债券、股票和房地产的价格都会受到影响。",
        "_card_index": 1
    }

    try:
        result = _render_card_internal(
            card=sample_card,
            background_image_path=None,
            output_path=os.path.join(DEFAULT_OUTPUT_DIR, "card_test.png"),
            card_index=1,
            total_cards=5
        )
        print("✅ card_theme_engine 自测成功：")
        print(result)
    except Exception as e:
        print("❌ card_theme_engine 自测失败：")
        print(str(e))