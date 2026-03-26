import os
import json
import random

from PIL import Image, ImageDraw, ImageFont

from moviepy import (
    ImageClip,
    AudioFileClip,
    CompositeAudioClip,
    concatenate_videoclips
)

from moviepy.video.fx.FadeIn import FadeIn
from moviepy.video.fx.FadeOut import FadeOut
from moviepy.video.fx.Resize import Resize

from gtts import gTTS


# ==============================
# 基础路径
# ==============================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SCRIPT_PATH = os.path.join(BASE_DIR, "script.json")
TAG_RULE_PATH = os.path.join(BASE_DIR, "tag_rules.json")
INDEX_PATH = os.path.join(BASE_DIR, "image_index.json")
PROFILE_PATH = os.path.join(BASE_DIR, "video_profile.json")

IMAGE_DIR = os.path.join(BASE_DIR, "images")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
MUSIC_DIR = os.path.join(BASE_DIR, "music")
BGM_PATH = os.path.join(MUSIC_DIR, "bgm.mp3")

os.makedirs(OUTPUT_DIR, exist_ok=True)


# ==============================
# 默认配置（防止 profile 缺字段）
# ==============================

DEFAULT_PROFILE = {
    "min_card_duration": 2.5,
    "fade_in": 0.3,
    "fade_out": 0.3,
    "zoom_speed": 0.02,
    "fps": 30,
    "bgm_volume": 0.15,
    "voice_volume": 1.0,
    "transition_mode": "random",
    "transition_templates": ["zoom_in", "zoom_out", "static"],
    "video_width": 1080,
    "video_height": 1920,
    "title_ratio": 0.15,
    "image_ratio": 0.70,
    "caption_ratio": 0.15
}


# ==============================
# 安全读取 JSON
# ==============================

def load_json_file(path, default_value):
    if not os.path.exists(path):
        print(f"未找到文件：{os.path.basename(path)}，将使用默认值。")
        return default_value

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"读取 JSON 失败：{path}，将使用默认值。错误：{e}")
        return default_value


def merge_profile(default_profile, custom_profile):
    merged = dict(default_profile)

    if isinstance(custom_profile, dict):
        for key, value in custom_profile.items():
            merged[key] = value

    return merged


# ==============================
# 读取配置文件
# ==============================

script = load_json_file(SCRIPT_PATH, {})
tag_rules = load_json_file(TAG_RULE_PATH, {"rules": []})
image_index = load_json_file(INDEX_PATH, [])
video_profile_raw = load_json_file(PROFILE_PATH, DEFAULT_PROFILE)

video_profile = merge_profile(DEFAULT_PROFILE, video_profile_raw)


# ==============================
# 从 profile 读取参数
# ==============================

VIDEO_WIDTH = int(video_profile.get("video_width", 1080))
VIDEO_HEIGHT = int(video_profile.get("video_height", 1920))

TITLE_RATIO = float(video_profile.get("title_ratio", 0.15))
IMAGE_RATIO = float(video_profile.get("image_ratio", 0.70))
CAPTION_RATIO = float(video_profile.get("caption_ratio", 0.15))

TITLE_H = int(VIDEO_HEIGHT * TITLE_RATIO)
IMAGE_H = int(VIDEO_HEIGHT * IMAGE_RATIO)
CAPTION_H = VIDEO_HEIGHT - TITLE_H - IMAGE_H

MIN_CARD_DURATION = float(video_profile.get("min_card_duration", 2.5))
FADE_IN_DURATION = float(video_profile.get("fade_in", 0.3))
FADE_OUT_DURATION = float(video_profile.get("fade_out", 0.3))
ZOOM_SPEED = float(video_profile.get("zoom_speed", 0.02))
FPS = int(video_profile.get("fps", 30))
BGM_VOLUME = float(video_profile.get("bgm_volume", 0.15))
VOICE_VOLUME = float(video_profile.get("voice_volume", 1.0))
TRANSITION_MODE = str(video_profile.get("transition_mode", "random")).strip().lower()

TRANSITION_TEMPLATES = video_profile.get("transition_templates", ["zoom_in", "zoom_out", "static"])
if not isinstance(TRANSITION_TEMPLATES, list) or not TRANSITION_TEMPLATES:
    TRANSITION_TEMPLATES = ["zoom_in", "zoom_out", "static"]


# ==============================
# 读取 script 内容
# ==============================

cards = script.get("cards", [])
voiceover = script.get("voiceover", "")

if not cards:
    raise ValueError("script.json 中没有 cards 数据。")

if not voiceover:
    raise ValueError("script.json 中没有 voiceover 数据。")


# ==============================
# 读取 images 文件夹中的图片（fallback 用）
# ==============================

image_files = [
    f for f in os.listdir(IMAGE_DIR)
    if f.lower().endswith((".png", ".jpg", ".jpeg"))
]

image_files.sort()

if not image_files:
    raise ValueError("images 文件夹中没有图片（png/jpg/jpeg）。")


# ==============================
# 字体加载
# ==============================

def load_font(size):
    font_candidates = [
        "arial.ttf",
        "msyh.ttc",
        "simhei.ttf"
    ]

    for font_name in font_candidates:
        try:
            return ImageFont.truetype(font_name, size)
        except:
            continue

    return ImageFont.load_default()


title_font = load_font(60)
caption_font = load_font(42)


# ==============================
# 文本安全处理
# ==============================

def safe_text(value):
    if value is None:
        return ""
    return str(value).strip()


# ==============================
# 文本换行
# ==============================

def wrap_text(draw, text, font, max_width):
    text = safe_text(text)

    if not text:
        return [""]

    lines = []
    current_line = ""

    for char in text:
        test_line = current_line + char
        bbox = draw.textbbox((0, 0), test_line, font=font)
        text_width = bbox[2] - bbox[0]

        if text_width <= max_width:
            current_line = test_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = char

    if current_line:
        lines.append(current_line)

    return lines


# ==============================
# 从 title + caption 提取 tags
# ==============================

def extract_tags(text, tag_rules_data):
    text = safe_text(text)
    found_tags = []

    for rule in tag_rules_data.get("rules", []):
        keyword = safe_text(rule.get("keyword", ""))
        tags = rule.get("tags", [])

        if keyword and keyword in text:
            for tag in tags:
                tag = safe_text(tag).lower()
                if tag and tag not in found_tags:
                    found_tags.append(tag)

    return found_tags


# ==============================
# 图片匹配
# ==============================

def find_best_image(search_tags, image_index_data):
    if not search_tags:
        return None

    best_item = None
    best_score = 0

    for item in image_index_data:
        file_name = safe_text(item.get("file", "")).lower()
        item_tags = item.get("tags", [])
        item_tags = [safe_text(t).lower() for t in item_tags]

        score = 0

        for tag in search_tags:
            tag = safe_text(tag).lower()

            if not tag:
                continue

            if tag in file_name:
                score += 1

            if tag in item_tags:
                score += 2

        if score > best_score:
            best_score = score
            best_item = item

    return best_item


# ==============================
# 确定图片路径
# 优先：
# 1. card 自带 image 字段
# 2. 规则匹配
# 3. fallback 顺序取图
# ==============================

def resolve_image_path(card, card_index):
    explicit_image = safe_text(card.get("image", ""))

    if explicit_image:
        explicit_path = os.path.join(IMAGE_DIR, explicit_image)
        if os.path.exists(explicit_path):
            print(f"[卡片 {card_index + 1}] 使用 script 指定图片: {explicit_image}")
            return explicit_path

    title = safe_text(card.get("title", ""))
    caption = safe_text(card.get("caption", ""))
    merged_text = f"{title} {caption}"

    search_tags = extract_tags(merged_text, tag_rules)
    result = find_best_image(search_tags, image_index)

    if result:
        matched_path = safe_text(result.get("path", ""))
        if matched_path and os.path.exists(matched_path):
            print(
                f"[卡片 {card_index + 1}] 自动匹配图片成功: "
                f"{os.path.basename(matched_path)} | tags={search_tags}"
            )
            return matched_path

    fallback_file = image_files[card_index % len(image_files)]
    fallback_path = os.path.join(IMAGE_DIR, fallback_file)

    print(f"[卡片 {card_index + 1}] 未匹配到合适图片，使用 fallback: {fallback_file}")
    return fallback_path


# ==============================
# 图片裁切填充（避免拉伸变形）
# ==============================

def cover_resize(image, target_width, target_height):
    src_w, src_h = image.size
    src_ratio = src_w / src_h
    target_ratio = target_width / target_height

    if src_ratio > target_ratio:
        new_height = target_height
        new_width = int(new_height * src_ratio)
    else:
        new_width = target_width
        new_height = int(new_width / src_ratio)

    image = image.resize((new_width, new_height))

    left = (new_width - target_width) // 2
    top = (new_height - target_height) // 2
    right = left + target_width
    bottom = top + target_height

    return image.crop((left, top, right, bottom))


# ==============================
# 选择模板
# ==============================

def choose_template():
    normalized_templates = []

    for item in TRANSITION_TEMPLATES:
        t = safe_text(item).lower()
        if t in ["zoom_in", "zoom_out", "static"]:
            normalized_templates.append(t)

    if not normalized_templates:
        normalized_templates = ["zoom_in", "zoom_out", "static"]

    if TRANSITION_MODE in ["zoom_in", "zoom_out", "static"]:
        return TRANSITION_MODE

    return random.choice(normalized_templates)


# ==============================
# 生成图卡 PNG
# ==============================

card_paths = []

for i, card in enumerate(cards):
    title = safe_text(card.get("title", ""))
    caption = safe_text(card.get("caption", ""))

    canvas = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), "white")
    draw = ImageDraw.Draw(canvas)

    # 标题区背景
    draw.rectangle([0, 0, VIDEO_WIDTH, TITLE_H], fill=(245, 245, 245))

    # 标题文字
    title_lines = wrap_text(draw, title, title_font, VIDEO_WIDTH - 120)
    title_line_height = 72
    total_title_height = len(title_lines) * title_line_height
    title_start_y = max(20, (TITLE_H - total_title_height) // 2)

    for line_idx, line in enumerate(title_lines):
        y = title_start_y + line_idx * title_line_height
        draw.text(
            (VIDEO_WIDTH // 2, y),
            line,
            fill="black",
            font=title_font,
            anchor="ma"
        )

    # 图片区
    image_path = resolve_image_path(card, i)

    try:
        picture = Image.open(image_path).convert("RGB")
        picture = cover_resize(picture, VIDEO_WIDTH, IMAGE_H)
        canvas.paste(picture, (0, TITLE_H))
    except Exception as e:
        print(f"[卡片 {i + 1}] 图片读取失败，使用灰色占位图。错误：{e}")
        placeholder = Image.new("RGB", (VIDEO_WIDTH, IMAGE_H), (220, 220, 220))
        canvas.paste(placeholder, (0, TITLE_H))

    # 说明区背景
    caption_top = TITLE_H + IMAGE_H
    draw.rectangle([0, caption_top, VIDEO_WIDTH, VIDEO_HEIGHT], fill=(248, 248, 248))

    # 说明文字
    caption_lines = wrap_text(draw, caption, caption_font, VIDEO_WIDTH - 120)
    caption_line_height = 54
    total_caption_height = len(caption_lines) * caption_line_height
    caption_start_y = caption_top + max(20, (CAPTION_H - total_caption_height) // 2)

    for line_idx, line in enumerate(caption_lines):
        y = caption_start_y + line_idx * caption_line_height
        draw.text(
            (VIDEO_WIDTH // 2, y),
            line,
            fill="black",
            font=caption_font,
            anchor="ma"
        )

    card_path = os.path.join(OUTPUT_DIR, f"card_{i + 1}.png")
    canvas.save(card_path)
    card_paths.append(card_path)

print("图卡生成完成")


# ==============================
# 生成语音
# ==============================

voice_path = os.path.join(OUTPUT_DIR, "voice.mp3")

tts = gTTS(voiceover, lang="zh-CN")
tts.save(voice_path)

voice_clip = AudioFileClip(voice_path)

print("语音生成完成")


# ==============================
# 视频时长分配
# 目前仍然采用“总语音 ÷ 卡片数”
# 但最短时长来自 profile，可配置
# ==============================

duration_per_card = max(MIN_CARD_DURATION, voice_clip.duration / len(card_paths))


# ==============================
# 生成视频片段
# ==============================

clips = []

for path in card_paths:
    template = choose_template()

    clip = ImageClip(path).with_duration(duration_per_card)

    effects = []

    if template == "zoom_in":
        effects.append(Resize(lambda t: 1 + ZOOM_SPEED * t))

    elif template == "zoom_out":
        effects.append(Resize(lambda t: 1 + ZOOM_SPEED * (duration_per_card - t)))

    if FADE_IN_DURATION > 0:
        effects.append(FadeIn(FADE_IN_DURATION))

    if FADE_OUT_DURATION > 0:
        effects.append(FadeOut(FADE_OUT_DURATION))

    clip = clip.with_effects(effects)
    clips.append(clip)

video = concatenate_videoclips(clips, method="compose")


# ==============================
# 音频处理
# 默认仅人声
# 如果存在 bgm.mp3，则低音量叠加
# ==============================

if os.path.exists(BGM_PATH):
    try:
        bgm_clip = AudioFileClip(BGM_PATH)

        if bgm_clip.duration > video.duration:
            bgm_clip = bgm_clip.subclipped(0, video.duration)

        bgm_clip = bgm_clip.with_volume_scaled(BGM_VOLUME)
        voice_main = voice_clip.with_volume_scaled(VOICE_VOLUME)

        final_audio = CompositeAudioClip([voice_main, bgm_clip])
        video = video.with_audio(final_audio)

        print("背景音乐已加入")
    except Exception as e:
        print(f"背景音乐处理失败，改为仅使用人声。错误：{e}")
        video = video.with_audio(voice_clip.with_volume_scaled(VOICE_VOLUME))
else:
    video = video.with_audio(voice_clip.with_volume_scaled(VOICE_VOLUME))


# ==============================
# 导出视频（Windows 兼容增强版）
# ==============================

output_video = os.path.join(OUTPUT_DIR, "video.mp4")

video.write_videofile(
    output_video,
    codec="libx264",
    audio_codec="aac",
    audio_bitrate="192k",
    fps=FPS,
    preset="medium",
    ffmpeg_params=[
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        "-profile:v", "baseline",
        "-level", "3.0"
    ]
)

print("视频生成完成")
print(output_video)