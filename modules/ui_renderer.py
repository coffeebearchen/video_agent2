# -*- coding: utf-8 -*-
"""
文件名：ui_renderer.py
作用说明：
1. 负责中文字体查找
2. 负责文本换行与安全排版
3. 负责下方信息卡片的绘制
4. 负责普通文本、高亮文本与轻量强调样式的混合渲染

本次改动点：
1. 为关键词高亮补开关位
2. 为关键词强调样式补开关位
3. 支持 highlight_animation = pop / none
4. 保持旧调用方式兼容，不传 highlights 也能正常工作
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from modules.config import EXPRESSION_MODULES, PROJECT_ROOT, UI_CARD, ExpressionModulesConfig, UICardConfig


DEFAULT_HIGHLIGHT_COLOR = (255, 176, 92, 255)


def find_font_path(ui_config: UICardConfig = UI_CARD):
    """优先寻找可显示中文的字体。"""
    candidates = [Path(font_path) for font_path in ui_config.windows_font_candidates]
    candidates.extend(PROJECT_ROOT / relative_path for relative_path in ui_config.project_font_candidates)

    for font_path in candidates:
        if font_path.exists():
            return font_path

    raise FileNotFoundError("未找到可显示中文的字体，请检查 Windows 字体或项目 fonts 目录")


def _measure_text(draw, text, font):
    """测量文本宽高。"""
    sample_text = text if text else " "
    bbox = draw.textbbox((0, 0), sample_text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def normalize_highlights(highlights):
    """清洗 highlights，返回稳定、去重后的字符串列表。"""
    if not isinstance(highlights, list):
        return []

    normalized_items = []
    seen_items = set()
    for item in highlights:
        text = str(item or "").strip()
        if not text or text in seen_items:
            continue

        seen_items.add(text)
        normalized_items.append(text)

    return normalized_items


def get_allowed_highlight_animations():
    """返回允许的关键词强调样式类型。"""
    return ("pop", "none")


def normalize_highlight_animation(animation_name, expression_config: ExpressionModulesConfig = EXPRESSION_MODULES):
    """清洗 highlight_animation，非法值回退到配置默认值。"""
    normalized = str(animation_name or "").strip().lower()
    if normalized in get_allowed_highlight_animations():
        return normalized

    default_animation = str(expression_config.default_highlight_animation or "").strip().lower()
    if default_animation in get_allowed_highlight_animations():
        return default_animation

    return "none"


def get_highlight_emphasis_strength(expression_config: ExpressionModulesConfig = EXPRESSION_MODULES):
    """返回关键词强调强度，并做轻量范围约束。"""
    try:
        strength = float(expression_config.highlight_emphasis_strength)
    except (TypeError, ValueError):
        strength = 0.12

    return min(0.22, max(0.0, strength))


def split_text_by_highlights(text, highlights):
    """按 highlights 将文本切分为普通片段与高亮片段。"""
    normalized_text = str(text or "")
    normalized_highlights = normalize_highlights(highlights)
    if not normalized_text:
        return [{"text": "", "is_highlight": False}]

    if not normalized_highlights:
        return [{"text": normalized_text, "is_highlight": False}]

    ordered_highlights = sorted(normalized_highlights, key=len, reverse=True)
    segments = []
    buffer_text = []
    index = 0

    while index < len(normalized_text):
        matched_highlight = None
        for highlight in ordered_highlights:
            if normalized_text.startswith(highlight, index):
                matched_highlight = highlight
                break

        if matched_highlight is None:
            buffer_text.append(normalized_text[index])
            index += 1
            continue

        if buffer_text:
            segments.append({"text": "".join(buffer_text), "is_highlight": False})
            buffer_text = []

        segments.append({"text": matched_highlight, "is_highlight": True})
        index += len(matched_highlight)

    if buffer_text:
        segments.append({"text": "".join(buffer_text), "is_highlight": False})

    return segments or [{"text": normalized_text, "is_highlight": False}]


def measure_text_segment(draw, text, font):
    """计算单个文本片段宽度与高度。"""
    return _measure_text(draw, text, font)


def _get_text_height(draw, text, font):
    """获取文本高度，便于做基线附近的轻微居中。"""
    return _measure_text(draw, text, font)[1]


def _append_line_run(line_runs, text, is_highlight):
    """将同类文本合并到当前行，避免绘制时过多碎片。"""
    if not text:
        return

    if line_runs and line_runs[-1]["is_highlight"] == is_highlight:
        line_runs[-1]["text"] += text
        return

    line_runs.append({"text": text, "is_highlight": is_highlight})


def _flatten_segments_to_char_tokens(segments):
    """把片段展开为逐字 token，保证换行逻辑稳定。"""
    tokens = []
    for segment in segments:
        segment_text = str(segment.get("text", "") or "")
        is_highlight = bool(segment.get("is_highlight"))
        for char in segment_text:
            if char == "\n":
                tokens.append({"text": "\n", "is_highlight": False, "is_newline": True})
            else:
                tokens.append({"text": char, "is_highlight": is_highlight, "is_newline": False})
    return tokens


def _ellipsize_line_runs(draw, line_runs, font, max_width):
    """为最后一行追加省略号，并确保不超出最大宽度。"""
    ellipsis = "…"
    if not line_runs:
        return [{"text": ellipsis, "is_highlight": False}]

    while line_runs:
        last_run = line_runs[-1]
        if not last_run["text"]:
            line_runs.pop()
            continue

        candidate_runs = [dict(item) for item in line_runs]
        candidate_runs[-1]["text"] = candidate_runs[-1]["text"] + ellipsis
        candidate_width = sum(measure_text_segment(draw, item["text"], font)[0] for item in candidate_runs)
        if candidate_width <= max_width:
            line_runs[-1]["text"] += ellipsis
            return line_runs

        last_run["text"] = last_run["text"][:-1]
        if last_run["text"]:
            continue

        line_runs.pop()

    return [{"text": ellipsis, "is_highlight": False}]


def layout_rich_text_lines(text, highlights, draw, font, max_width, max_lines=None):
    """将普通文本与高亮文本混合排版为多行。"""
    if max_lines is None:
        max_lines = UI_CARD.max_lines

    normalized_text = str(text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized_text:
        return [[{"text": "", "is_highlight": False}]]

    text_segments = split_text_by_highlights(normalized_text, highlights)
    tokens = _flatten_segments_to_char_tokens(text_segments)

    lines = []
    current_line_runs = []
    current_line_text = ""
    was_truncated = False
    index = 0

    while index < len(tokens):
        token = tokens[index]
        if token["is_newline"]:
            lines.append(current_line_runs or [{"text": "", "is_highlight": False}])
            current_line_runs = []
            current_line_text = ""
            if len(lines) >= max_lines:
                was_truncated = index < len(tokens) - 1
                break
            index += 1
            continue

        candidate_text = f"{current_line_text}{token['text']}"
        candidate_width, _ = measure_text_segment(draw, candidate_text, font)
        if candidate_width <= max_width or not current_line_text:
            _append_line_run(current_line_runs, token["text"], token["is_highlight"])
            current_line_text = candidate_text
            index += 1
            continue

        lines.append(current_line_runs or [{"text": token["text"], "is_highlight": token["is_highlight"]}])
        current_line_runs = []
        current_line_text = ""
        if len(lines) >= max_lines:
            was_truncated = True
            break

    if len(lines) < max_lines and (current_line_runs or not lines):
        lines.append(current_line_runs or [{"text": "", "is_highlight": False}])

    if len(lines) > max_lines:
        lines = lines[:max_lines]
        was_truncated = True

    if was_truncated and lines:
        lines[-1] = _ellipsize_line_runs(draw, [dict(item) for item in lines[-1]], font, max_width)

    return lines or [[{"text": "", "is_highlight": False}]]


def _build_emphasis_font(font_path, ui_config: UICardConfig, expression_config: ExpressionModulesConfig):
    """为高亮强调构建轻微放大的字体。"""
    strength = get_highlight_emphasis_strength(expression_config)
    emphasized_size = max(ui_config.text_font_size + 2, int(round(ui_config.text_font_size * (1.0 + strength))))
    return ImageFont.truetype(str(font_path), emphasized_size)


def draw_highlight_run_with_emphasis(
    draw,
    run_text,
    draw_x,
    draw_y,
    normal_font,
    emphasis_font,
    fill_color,
):
    """为高亮词绘制轻微 pop 强调样式，保持整体排版宽度稳定。"""
    normal_width, normal_height = measure_text_segment(draw, run_text, normal_font)
    emphasis_width, emphasis_height = measure_text_segment(draw, run_text, emphasis_font)

    emphasis_x = int(round(draw_x + (normal_width - emphasis_width) / 2.0))
    emphasis_y = int(round(draw_y + (normal_height - emphasis_height) / 2.0))

    glow_color = (255, 233, 196, 90)
    for offset_x, offset_y in ((0, -1), (0, 1), (-1, 0), (1, 0)):
        draw.text((emphasis_x + offset_x, emphasis_y + offset_y), run_text, font=emphasis_font, fill=glow_color)

    draw.text((emphasis_x, emphasis_y), run_text, font=emphasis_font, fill=fill_color)


def get_text_line_height(draw, font, emphasis_font=None):
    """返回当前排版使用的统一行高。"""
    base_height = _get_text_height(draw, "中", font)
    if emphasis_font is None:
        return base_height

    emphasis_height = _get_text_height(draw, "中", emphasis_font)
    return max(base_height, emphasis_height)


def draw_rich_text_lines(
    draw,
    text_x,
    start_y,
    lines,
    font,
    ui_config,
    expression_config: ExpressionModulesConfig = EXPRESSION_MODULES,
    highlight_animation=None,
    emphasis_font=None,
    highlight_color=DEFAULT_HIGHLIGHT_COLOR,
):
    """按混合文本排版结果逐行绘制文字。"""
    line_height = get_text_line_height(draw, font, emphasis_font)
    base_text_height = _get_text_height(draw, "中", font)
    highlight_enabled = bool(expression_config.highlight_enabled)
    emphasis_enabled = bool(expression_config.highlight_emphasis_enabled)
    normalized_highlight_animation = normalize_highlight_animation(highlight_animation, expression_config)
    current_y = start_y

    for line_runs in lines:
        current_x = text_x
        for run in line_runs:
            run_text = str(run.get("text", "") or "")
            if not run_text:
                continue

            run_width, _ = measure_text_segment(draw, run_text, font)
            draw_y = int(round(current_y + (line_height - base_text_height) / 2.0))
            is_highlight = bool(run.get("is_highlight")) and highlight_enabled
            if is_highlight:
                if emphasis_enabled and normalized_highlight_animation == "pop" and emphasis_font is not None:
                    draw_highlight_run_with_emphasis(
                        draw=draw,
                        run_text=run_text,
                        draw_x=current_x,
                        draw_y=draw_y,
                        normal_font=font,
                        emphasis_font=emphasis_font,
                        fill_color=highlight_color,
                    )
                else:
                    draw.text((current_x, draw_y), run_text, font=font, fill=highlight_color)
            else:
                draw.text((current_x, draw_y), run_text, font=font, fill=ui_config.text_color)

            current_x += run_width

        current_y += line_height + ui_config.text_line_spacing

    total_height = 0
    if lines:
        total_height = len(lines) * line_height + max(0, len(lines) - 1) * ui_config.text_line_spacing
    return total_height


def wrap_text(text, draw, font, max_width, max_lines=None):
    """按实际像素宽度做中文安全换行。"""
    rich_lines = layout_rich_text_lines(text, [], draw, font, max_width, max_lines)
    return ["".join(item["text"] for item in line_runs) for line_runs in rich_lines]


def render_info_card(text, width, height):
    """渲染下方信息卡片，返回透明 RGBA 图片。"""
    return render_info_card_with_config(text, width, height, UI_CARD)


def render_info_card_with_config(
    text,
    width,
    height,
    ui_config: UICardConfig,
    highlights=None,
    highlight_animation=None,
    expression_config: ExpressionModulesConfig = EXPRESSION_MODULES,
):
    """使用指定 UI 配置渲染下方信息卡片。"""
    font_path = find_font_path(ui_config)
    text_font = ImageFont.truetype(str(font_path), ui_config.text_font_size)
    label_font = ImageFont.truetype(str(font_path), ui_config.label_font_size)

    emphasis_font = None
    if expression_config.highlight_enabled and expression_config.highlight_emphasis_enabled:
        emphasis_font = _build_emphasis_font(font_path, ui_config, expression_config)

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    card_width = int(width * ui_config.card_width_ratio)
    text_area_width = card_width - ui_config.padding_x * 2
    active_highlights = normalize_highlights(highlights) if expression_config.highlight_enabled else []
    rich_text_lines = layout_rich_text_lines(
        text=text,
        highlights=active_highlights,
        draw=draw,
        font=text_font,
        max_width=text_area_width,
        max_lines=ui_config.max_lines,
    )

    _, label_height = _measure_text(draw, ui_config.label_text, label_font)
    text_line_height = get_text_line_height(draw, text_font, emphasis_font)
    text_block_height = len(rich_text_lines) * text_line_height + max(0, len(rich_text_lines) - 1) * ui_config.text_line_spacing
    content_height = label_height + ui_config.label_text_gap + text_block_height

    card_height = content_height + ui_config.padding_top + ui_config.padding_bottom
    max_card_height = int(height * ui_config.card_max_height_ratio)
    card_height = min(card_height, max_card_height)

    card_left = (width - card_width) // 2
    preferred_top = int(height * ui_config.card_top_ratio)
    max_top = height - card_height - ui_config.card_bottom_margin
    card_top = min(preferred_top, max_top)
    card_top = max(card_top, int(height * 0.58))
    card_right = card_left + card_width
    card_bottom = card_top + card_height

    draw.rounded_rectangle(
        (card_left, card_top, card_right, card_bottom),
        radius=ui_config.card_radius,
        fill=ui_config.card_fill,
        outline=ui_config.card_border,
        width=ui_config.card_border_width,
    )

    text_x = card_left + ui_config.padding_x
    current_y = card_top + ui_config.padding_top
    draw.text((text_x, current_y), ui_config.label_text, font=label_font, fill=ui_config.title_color)
    current_y += label_height + ui_config.label_text_gap

    available_text_height = card_bottom - ui_config.padding_bottom - current_y
    max_visible_lines = 0
    if text_line_height + ui_config.text_line_spacing > 0:
        max_visible_lines = max(
            0,
            (available_text_height + ui_config.text_line_spacing) // (text_line_height + ui_config.text_line_spacing),
        )

    visible_lines = rich_text_lines[:max_visible_lines] if max_visible_lines > 0 else []
    draw_rich_text_lines(
        draw=draw,
        text_x=text_x,
        start_y=current_y,
        lines=visible_lines,
        font=text_font,
        ui_config=ui_config,
        expression_config=expression_config,
        highlight_animation=highlight_animation,
        emphasis_font=emphasis_font,
    )

    return overlay
