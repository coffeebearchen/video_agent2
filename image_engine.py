import os
import json
import re
from typing import List, Tuple
from PIL import Image, ImageDraw, ImageFont

# ======================================
# OUTPUT CONTRACT (DO NOT CHANGE)
# ======================================
# Canvas Ratio : 4:5
# Canvas Size  : 1080 x 1350
# Final Output : images/flat/card_x.png
# Do not change ratio / crop / scaling
# unless explicitly approved by user.
# ======================================

BASE_WIDTH = 1080
BASE_HEIGHT = 1350

BG_DIR = "images/bg"
OUT_DIR = "images"

TEXT_DIR = os.path.join(OUT_DIR, "text")
OVERLAY_DIR = os.path.join(OUT_DIR, "overlay")
FLAT_DIR = os.path.join(OUT_DIR, "flat")

for d in [TEXT_DIR, OVERLAY_DIR, FLAT_DIR]:
    os.makedirs(d, exist_ok=True)

FONT_PATH = "fonts/SourceHanSansCN-Bold.otf"

# 颜色
NORMAL_COLOR = (255, 255, 255, 255)
HIGHLIGHT_COLOR = (255, 140, 0, 255)
STROKE_FILL = (0, 0, 0, 180)

# 遮罩
OVERLAY_ALPHA = 115

# 布局规则（保持当前视觉风格，不改输出契约）
LAYOUT_RULES = {
    "hook": {"fontsize": 84, "highlight_size": 98, "position": "center"},
    "concept": {"fontsize": 74, "highlight_size": 88, "position": "center"},
    "analogy": {"fontsize": 72, "highlight_size": 86, "position": "lower"},
    "example": {"fontsize": 72, "highlight_size": 86, "position": "lower"},
    "insight": {"fontsize": 78, "highlight_size": 92, "position": "center"},
}

# 行距
LINE_SPACING = 10

# 优先 2 行，必要时 3 行
PREFERRED_MAX_LINES = 2
ABSOLUTE_MAX_LINES = 3

# 文本块最大可用宽度（按画面比例控制，不让字贴边）
TEXT_MAX_WIDTH_RATIO = 0.72

# 超宽时最小允许字号，防止无限缩小
MIN_NORMAL_FONT_SIZE = 46
MIN_HIGHLIGHT_FONT_SIZE = 56

# 用于自然断句的短语连接点
BREAK_TOKENS_LONG = [
    "而不是", "而是", "不是", "其实", "因为", "所以", "如果", "但是", "然而",
    "背后", "面对", "关键", "核心", "真正", "往往"
]

BREAK_TOKENS_SHORT = [
    "比", "和", "与", "像", "对", "把", "在", "让", "更", "会"
]


# ======================================
# 基础工具
# ======================================

def ensure_font():
    if not os.path.exists(FONT_PATH):
        raise FileNotFoundError(
            f"字体文件不存在：{FONT_PATH}\n"
            f"请确认字体文件已放到该路径。"
        )


def list_bg_files():
    if not os.path.exists(BG_DIR):
        raise FileNotFoundError(f"背景图目录不存在：{BG_DIR}")

    files = []
    for f in os.listdir(BG_DIR):
        lower = f.lower()
        if lower.endswith(".jpg") or lower.endswith(".jpeg") or lower.endswith(".png"):
            files.append(f)

    files.sort()

    if not files:
        raise Exception("bg folder empty")

    return files


def select_background(card_index: int) -> str:
    bg_files = list_bg_files()
    bg_name = bg_files[card_index % len(bg_files)]
    return os.path.join(BG_DIR, bg_name)


def fit_crop_to_canvas(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """
    保持比例，不拉伸。
    先等比放大到覆盖画布，再居中裁剪。
    """
    src_w, src_h = img.size
    src_ratio = src_w / src_h
    target_ratio = target_w / target_h

    if src_ratio > target_ratio:
        scale = target_h / src_h
    else:
        scale = target_w / src_w

    new_w = int(src_w * scale)
    new_h = int(src_h * scale)

    img = img.resize((new_w, new_h), Image.LANCZOS)

    left = (new_w - target_w) // 2
    top = (new_h - target_h) // 2
    right = left + target_w
    bottom = top + target_h

    return img.crop((left, top, right, bottom))


def create_overlay() -> Image.Image:
    return Image.new("RGBA", (BASE_WIDTH, BASE_HEIGHT), (0, 0, 0, OVERLAY_ALPHA))


# ======================================
# 文本清理
# ======================================

def clean_text(text: str) -> str:
    """
    清理规则：
    - 去掉括号
    - 去掉中英文常见标点
    - 压缩空白
    """
    if text is None:
        return ""

    text = str(text).strip()
    text = re.sub(r"[，。！？：；、,\.!?;:()\[\]{}（）【】<>《》“”\"'‘’`~…—\-]", "", text)
    text = re.sub(r"\s+", "", text)
    return text.strip()


def get_highlight_list(card: dict) -> List[str]:
    highlights = card.get("highlight", card.get("highlights", []))
    if not isinstance(highlights, list):
        return []

    result = []
    for item in highlights:
        if isinstance(item, str):
            word = clean_text(item)
            if word and word not in result:
                result.append(word)
    return result[:2]


# ======================================
# 断句：短语级切分，而不是按字符硬切
# ======================================

def split_into_phrases(text: str) -> List[str]:
    """
    把一句话切成较自然的短语块。
    优先按较长连接词切，再按较短连接点切。
    不做最终分行，只做 phrase 列表。
    """
    text = clean_text(text)
    if not text:
        return []

    phrases = [text]

    # 先按长连接词切
    for token in BREAK_TOKENS_LONG:
        new_phrases = []
        for phrase in phrases:
            if token in phrase and len(phrase) > len(token) + 2:
                parts = phrase.split(token)
                for i, part in enumerate(parts):
                    if not part:
                        continue
                    if i < len(parts) - 1:
                        new_phrases.append(part + token)
                    else:
                        new_phrases.append(part)
            else:
                new_phrases.append(phrase)
        phrases = new_phrases

    # 再按短连接点补充切分，但尽量不切得太碎
    final_phrases = []
    for phrase in phrases:
        if len(phrase) <= 8:
            final_phrases.append(phrase)
            continue

        cut_done = False
        for token in BREAK_TOKENS_SHORT:
            idx = phrase.find(token, 4)
            if idx != -1 and idx < len(phrase) - 2:
                left = phrase[:idx]
                right = phrase[idx:]
                if left:
                    final_phrases.append(left)
                if right:
                    final_phrases.append(right)
                cut_done = True
                break

        if not cut_done:
            final_phrases.append(phrase)

    # 去空
    return [p for p in final_phrases if p]


# ======================================
# 高亮样式
# ======================================

def build_char_styles(text: str, highlights: List[str]) -> List[Tuple[str, bool]]:
    """
    将文本拆成 (字符, 是否高亮)。
    重点词优先匹配长词，避免重叠混乱。
    """
    if not text:
        return []

    if not highlights:
        return [(ch, False) for ch in text]

    highlights = sorted(highlights, key=len, reverse=True)
    styles = [False] * len(text)

    for word in highlights:
        start = 0
        while True:
            idx = text.find(word, start)
            if idx == -1:
                break
            for i in range(idx, idx + len(word)):
                if 0 <= i < len(styles):
                    styles[i] = True
            start = idx + len(word)

    return [(text[i], styles[i]) for i in range(len(text))]


def segment_line(line: List[Tuple[str, bool]]) -> List[Tuple[str, bool]]:
    """
    把一行连续字符合并成样式段。
    例如：
    [('真',False),('正',False),('速',True)] ->
    [('真正',False),('速',True)]
    """
    if not line:
        return []

    segments = []
    buf = line[0][0]
    state = line[0][1]

    for ch, is_hl in line[1:]:
        if is_hl == state:
            buf += ch
        else:
            segments.append((buf, state))
            buf = ch
            state = is_hl

    segments.append((buf, state))
    return segments


# ======================================
# 测量与对齐
# ======================================

def measure_bbox(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.FreeTypeFont):
    return draw.textbbox((0, 0), text, font=font, stroke_width=3)


def measure_segment_width(draw: ImageDraw.ImageDraw, seg_text: str, font: ImageFont.FreeTypeFont) -> int:
    bbox = measure_bbox(draw, seg_text, font)
    return bbox[2] - bbox[0]


def measure_segment_height(draw: ImageDraw.ImageDraw, seg_text: str, font: ImageFont.FreeTypeFont) -> int:
    bbox = measure_bbox(draw, seg_text, font)
    return bbox[3] - bbox[1]


def measure_line_width(draw: ImageDraw.ImageDraw, normal_font, highlight_font, line_segments) -> int:
    total = 0
    for seg_text, is_hl in line_segments:
        font = highlight_font if is_hl else normal_font
        total += measure_segment_width(draw, seg_text, font)
    return total


def calc_block_position(text_w: int, text_h: int, position_mode: str) -> Tuple[int, int]:
    x = (BASE_WIDTH - text_w) // 2

    if position_mode == "center":
        y = (BASE_HEIGHT - text_h) // 2
    elif position_mode == "lower":
        y = int(BASE_HEIGHT * 0.63)
    else:
        y = (BASE_HEIGHT - text_h) // 2

    return x, y


def draw_line_center_aligned(draw: ImageDraw.ImageDraw, line_segments, normal_font, highlight_font, line_top_y: int) -> int:
    """
    橙字与白字按“视觉中线”对齐。
    不是顶部对齐，也不是下边对齐。
    """
    line_width = measure_line_width(draw, normal_font, highlight_font, line_segments)
    current_x = (BASE_WIDTH - line_width) // 2

    boxes = []
    for seg_text, is_hl in line_segments:
        font = highlight_font if is_hl else normal_font
        bbox = measure_bbox(draw, seg_text, font)
        boxes.append((seg_text, is_hl, font, bbox))

    line_top = min(b[3][1] for b in boxes) if boxes else 0
    line_bottom = max(b[3][3] for b in boxes) if boxes else 0
    line_box_h = line_bottom - line_top
    line_center_y = line_top_y + line_box_h / 2

    for seg_text, is_hl, font, bbox in boxes:
        seg_w = bbox[2] - bbox[0]
        seg_center_offset = (bbox[1] + bbox[3]) / 2
        draw_y = int(line_center_y - seg_center_offset)

        fill_color = HIGHLIGHT_COLOR if is_hl else NORMAL_COLOR

        draw.text(
            (current_x, draw_y),
            seg_text,
            font=font,
            fill=fill_color,
            stroke_width=3,
            stroke_fill=STROKE_FILL
        )

        current_x += seg_w

    return int(line_box_h)


# ======================================
# 核心：本地智能断句（按像素宽度排版）
# ======================================

def build_lines_by_pixel_width(draw, phrases: List[str], highlights: List[str], normal_font, highlight_font, max_width: int) -> List[str]:
    """
    将短语按像素宽度组行。
    不是按字符数，而是按真实渲染宽度。
    """
    if not phrases:
        return [""]

    lines = []
    current = ""

    for phrase in phrases:
        candidate = current + phrase if current else phrase

        styled = build_char_styles(candidate, highlights)
        segments = segment_line(styled)
        width = measure_line_width(draw, normal_font, highlight_font, segments)

        if width <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
                current = phrase
            else:
                # 单个 phrase 本身就太长，退化为按字符保守切
                part = phrase
                tmp = ""
                for ch in part:
                    test = tmp + ch
                    styled2 = build_char_styles(test, highlights)
                    segs2 = segment_line(styled2)
                    w2 = measure_line_width(draw, normal_font, highlight_font, segs2)
                    if w2 <= max_width:
                        tmp = test
                    else:
                        if tmp:
                            lines.append(tmp)
                        tmp = ch
                current = tmp

    if current:
        lines.append(current)

    return [x for x in lines if x]


def auto_layout_lines(draw, text: str, highlights: List[str], base_size: int, hl_size: int, max_width: int):
    """
    自动排版策略：
    1. 先按 phrase 切
    2. 按像素宽度排成 2 行优先
    3. 如果超过 3 行，就降字号重试
    4. 直到达到可接受排版或到最小字号
    """
    text = clean_text(text)
    if not text:
        return [""]

    phrases = split_into_phrases(text)
    if not phrases:
        phrases = [text]

    normal_size = base_size
    highlight_size = hl_size

    while True:
        normal_font = ImageFont.truetype(FONT_PATH, normal_size)
        highlight_font = ImageFont.truetype(FONT_PATH, highlight_size)

        lines = build_lines_by_pixel_width(
            draw=draw,
            phrases=phrases,
            highlights=highlights,
            normal_font=normal_font,
            highlight_font=highlight_font,
            max_width=max_width
        )

        if len(lines) <= PREFERRED_MAX_LINES:
            return lines, normal_size, highlight_size

        if len(lines) <= ABSOLUTE_MAX_LINES:
            return lines, normal_size, highlight_size

        # 超过 3 行，缩字再试
        normal_size -= 4
        highlight_size -= 4

        if normal_size < MIN_NORMAL_FONT_SIZE or highlight_size < MIN_HIGHLIGHT_FONT_SIZE:
            # 到底线了，强行截到 3 行
            return lines[:ABSOLUTE_MAX_LINES], max(normal_size, MIN_NORMAL_FONT_SIZE), max(highlight_size, MIN_HIGHLIGHT_FONT_SIZE)


# ======================================
# 文字层
# ======================================

def create_text_layer(text: str, card_type: str, highlights: List[str]) -> Image.Image:
    rule = LAYOUT_RULES.get(card_type, LAYOUT_RULES["concept"])

    base_size = rule["fontsize"]
    highlight_size = rule["highlight_size"]
    position_mode = rule["position"]

    img = Image.new("RGBA", (BASE_WIDTH, BASE_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    max_text_width = int(BASE_WIDTH * TEXT_MAX_WIDTH_RATIO)

    lines, final_normal_size, final_highlight_size = auto_layout_lines(
        draw=draw,
        text=text,
        highlights=highlights,
        base_size=base_size,
        hl_size=highlight_size,
        max_width=max_text_width
    )

    normal_font = ImageFont.truetype(FONT_PATH, final_normal_size)
    highlight_font = ImageFont.truetype(FONT_PATH, final_highlight_size)

    segmented_lines = []
    line_widths = []
    line_heights = []

    for line in lines:
        styled_chars = build_char_styles(line, highlights)
        segs = segment_line(styled_chars)
        segmented_lines.append(segs)

        line_w = measure_line_width(draw, normal_font, highlight_font, segs)
        line_widths.append(line_w)

        boxes = []
        for seg_text, is_hl in segs:
            font = highlight_font if is_hl else normal_font
            boxes.append(measure_bbox(draw, seg_text, font))

        if boxes:
            top = min(b[1] for b in boxes)
            bottom = max(b[3] for b in boxes)
            line_h = bottom - top
        else:
            line_h = final_normal_size

        line_heights.append(int(line_h))

    block_w = max(line_widths) if line_widths else 0
    block_h = sum(line_heights) + LINE_SPACING * (len(line_heights) - 1)

    _, start_y = calc_block_position(block_w, block_h, position_mode)
    current_y = start_y

    for idx, segs in enumerate(segmented_lines):
        line_h = draw_line_center_aligned(draw, segs, normal_font, highlight_font, current_y)
        current_y += line_h + LINE_SPACING

    return img


# ======================================
# 文件保存
# ======================================

def save_rgba_png(img: Image.Image, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, format="PNG")


def save_rgb_png(img: Image.Image, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.convert("RGB").save(path, format="PNG")


# ======================================
# 主函数（接口兼容）
# ======================================

def generate_images(script_path: str = "script.json"):
    ensure_font()

    if not os.path.exists(script_path):
        raise FileNotFoundError(f"script 文件不存在：{script_path}")

    with open(script_path, "r", encoding="utf8") as f:
        data = json.load(f)

    cards = data.get("cards", [])
    if not cards:
        raise Exception("script.json 中没有 cards")

    flat_paths = []

    for i, card in enumerate(cards):
        text = str(card.get("text", "")).strip()
        ctype = str(card.get("type", "concept")).strip().lower()
        highlights = get_highlight_list(card)

        bg_path = select_background(i)
        bg = Image.open(bg_path).convert("RGBA")
        bg = fit_crop_to_canvas(bg, BASE_WIDTH, BASE_HEIGHT)

        overlay = create_overlay()
        text_layer = create_text_layer(text, ctype, highlights)

        overlay_path = os.path.join(OVERLAY_DIR, f"card_{i}.png")
        text_path = os.path.join(TEXT_DIR, f"card_{i}.png")

        save_rgba_png(overlay, overlay_path)
        save_rgba_png(text_layer, text_path)

        flat = Image.alpha_composite(bg, overlay)
        flat = Image.alpha_composite(flat, text_layer)

        flat_path = os.path.join(FLAT_DIR, f"card_{i}.png")
        save_rgb_png(flat, flat_path)

        flat_paths.append(flat_path)

        print(f"已生成分层与预览: card_{i}")

    return flat_paths


if __name__ == "__main__":
    result = generate_images("script.json")
    print(result)