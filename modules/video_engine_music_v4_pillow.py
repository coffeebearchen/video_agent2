# video_engine_music_v4_pillow.py
# -*- coding: utf-8 -*-

"""
知识图卡视频引擎 v4 Pillow 版

特点：
1. 不依赖 ImageMagick
2. 用 Pillow 生成文字图层
3. 支持文字淡入
4. 支持高亮词强调
5. 支持背景轻微镜头运动
6. 支持转场
7. 支持背景音乐
8. 保持 1080x1350 / 4:5 契约

重要说明：
- 如果你当前 images/flat/card_x.png 里已经带文字，
  再叠加文字层会重复。
- 因此本版本优先寻找纯背景图目录：
    images/bg_layer/card_0.png ~ card_4.png
- 如果找不到，则自动退回 images/flat/
  并自动关闭文字叠加，避免双字。

运行：
python video_engine_music_v4_pillow.py
"""

import json
from pathlib import Path
from typing import List, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    concatenate_videoclips,
    afx,
)

# =========================
# 基础路径
# =========================
BASE_DIR = Path(__file__).resolve().parent

FLAT_DIR = BASE_DIR / "images" / "flat"
BG_LAYER_DIR = BASE_DIR / "images" / "bg_layer"
MUSIC_DIR = BASE_DIR / "assets" / "music"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_FILE = OUTPUT_DIR / "video.mp4"
SCRIPT_FILE = BASE_DIR / "script.json"

# =========================
# 输出契约（冻结）
# =========================
VIDEO_W = 1080
VIDEO_H = 1350
FPS = 24

# =========================
# 图卡时长
# =========================
CARD_DURATIONS = [2.6, 3.0, 3.2, 3.2, 2.8]

# =========================
# 背景动作（让画面有流动感）
# 可选：
# zoom_in / zoom_out / pan_left / pan_right / pan_up / pan_down / static
# =========================
CARD_MOTIONS = [
    "zoom_in",
    "pan_left",
    "zoom_out",
    "pan_right",
    "zoom_in",
]

# =========================
# 转场配置（共4段）
# 0->1, 1->2, 2->3, 3->4
# 可选：
# crossfade / slide_left / slide_right / pause_cut
# =========================
TRANSITIONS = [
    "crossfade",
    "slide_left",
    "pause_cut",
    "crossfade",
]

CROSSFADE_DURATION = 0.45
SLIDE_DURATION = 0.42
PAUSE_DURATION = 0.18

# =========================
# 缩放 / 平移参数
# =========================
ZOOM_IN_START = 1.00
ZOOM_IN_END = 1.08

ZOOM_OUT_START = 1.08
ZOOM_OUT_END = 1.00

PAN_DISTANCE_X = 60
PAN_DISTANCE_Y = 50

# =========================
# 音乐参数
# =========================
AUDIO_VOLUME = 0.22
MUSIC_START_SEC = 20
AUDIO_FADEIN_SEC = 0.6
AUDIO_FADEOUT_SEC = 0.8

# =========================
# 文字图层参数
# =========================
TEXT_FADEIN_SEC = 0.35
HIGHLIGHT_START_SEC = 0.75
HIGHLIGHT_DURATION = 0.85
HIGHLIGHT_SCALE_END = 1.06

TEXT_BOX_W = 820
TEXT_CENTER_X = VIDEO_W // 2
TEXT_CENTER_Y = VIDEO_H // 2

NORMAL_FONT_SIZE = 68
HIGHLIGHT_FONT_SIZE = 70
LINE_SPACING = 18

NORMAL_TEXT_COLOR = (255, 255, 255, 255)
HIGHLIGHT_TEXT_COLOR = (255, 165, 0, 255)  # 橙色

BG_COLOR = (0, 0, 0)

# 如果没有纯背景图，这里会自动关掉，避免双字
ENABLE_TEXT_OVERLAY = True


# =========================
# 基础工具
# =========================
def load_script():
    if not SCRIPT_FILE.exists():
        raise FileNotFoundError(f"未找到 script.json：{SCRIPT_FILE}")
    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def find_music_file() -> Path:
    if not MUSIC_DIR.exists():
        raise FileNotFoundError(f"未找到音乐目录：{MUSIC_DIR}")

    preferred = [
        "bgm_test.mp3",
        "bgm_test.wav",
        "bgm_test.m4a",
    ]
    for name in preferred:
        p = MUSIC_DIR / name
        if p.exists():
            return p

    candidates = []
    for ext in ["*.mp3", "*.wav", "*.m4a"]:
        candidates.extend(MUSIC_DIR.glob(ext))

    if not candidates:
        raise FileNotFoundError("未找到背景音乐文件，请放到 assets/music/ 目录。")

    return sorted(candidates)[0]


def find_background_dir() -> Tuple[Path, bool]:
    """
    返回：
    - 背景目录
    - 是否启用文字 overlay

    规则：
    1. 如果 images/bg_layer/ 有 card_0~4，则认为是纯背景图，开启文字层
    2. 否则退回 images/flat/，关闭文字层，避免双字
    """
    bg_ready = True
    for i in range(5):
        if not (BG_LAYER_DIR / f"card_{i}.png").exists():
            bg_ready = False
            break

    if bg_ready:
        return BG_LAYER_DIR, True

    flat_ready = True
    for i in range(5):
        if not (FLAT_DIR / f"card_{i}.png").exists():
            flat_ready = False
            break

    if not flat_ready:
        raise FileNotFoundError(
            "既没有找到 images/bg_layer/card_0~4.png，也没有找到 images/flat/card_0~4.png"
        )

    return FLAT_DIR, False


def find_font_path() -> str:
    """
    Windows 常见中文字体路径优先级
    """
    candidates = [
        r"C:\Windows\Fonts\msyh.ttc",      # 微软雅黑
        r"C:\Windows\Fonts\msyhbd.ttc",
        r"C:\Windows\Fonts\simhei.ttf",    # 黑体
        r"C:\Windows\Fonts\simsun.ttc",    # 宋体
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for p in candidates:
        if Path(p).exists():
            return p
    return ""


FONT_PATH = find_font_path()


def make_bg(duration: float):
    return ColorClip(
        size=(VIDEO_W, VIDEO_H),
        color=BG_COLOR,
        duration=duration
    )


def pil_to_np(img: Image.Image):
    return np.array(img)


# =========================
# 文字排版相关
# =========================
def get_font(size: int):
    if FONT_PATH:
        return ImageFont.truetype(FONT_PATH, size=size)
    return ImageFont.load_default()


def text_size(draw: ImageDraw.ImageDraw, text: str, font) -> Tuple[int, int]:
    if not text:
        return 0, 0
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def wrap_text_by_width(text: str, font, max_width: int) -> List[str]:
    """
    按像素宽度换行。
    对中文按字符级处理，稳定、简单。
    """
    dummy_img = Image.new("RGBA", (10, 10), (0, 0, 0, 0))
    draw = ImageDraw.Draw(dummy_img)

    lines = []
    current = ""

    for ch in text:
        candidate = current + ch
        w, _ = text_size(draw, candidate, font)
        if w <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = ch

    if current:
        lines.append(current)

    return lines


def draw_multiline_text_image(
    text: str,
    highlight_words: List[str],
    normal_font_size: int = NORMAL_FONT_SIZE,
    highlight_font_size: int = HIGHLIGHT_FONT_SIZE,
    color_normal=NORMAL_TEXT_COLOR,
    color_highlight=HIGHLIGHT_TEXT_COLOR,
    canvas_w: int = VIDEO_W,
    canvas_h: int = VIDEO_H,
) -> Image.Image:
    """
    生成一张透明文字层 PNG（PIL Image）
    高亮词会用橙色绘制。
    """
    img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_normal = get_font(normal_font_size)
    font_high = get_font(highlight_font_size)

    lines = wrap_text_by_width(text, font_normal, TEXT_BOX_W)

    # 估算总高度
    line_heights = []
    for line in lines:
        _, h = text_size(draw, line, font_normal)
        line_heights.append(h)

    total_h = 0
    for i, h in enumerate(line_heights):
        total_h += h
        if i < len(line_heights) - 1:
            total_h += LINE_SPACING

    start_y = int(TEXT_CENTER_Y - total_h / 2)

    y = start_y
    for line_idx, line in enumerate(lines):
        line_w, line_h = text_size(draw, line, font_normal)
        x = int(TEXT_CENTER_X - line_w / 2)

        # 从左到右绘制，同时处理高亮词
        pos = 0
        while pos < len(line):
            matched = None
            for hw in sorted(highlight_words, key=len, reverse=True):
                if hw and line.startswith(hw, pos):
                    matched = hw
                    break

            if matched:
                seg = matched
                seg_font = font_high
                seg_color = color_highlight
            else:
                seg = line[pos]
                seg_font = font_normal
                seg_color = color_normal

            draw.text((x, y), seg, font=seg_font, fill=seg_color)
            seg_w, _ = text_size(draw, seg, seg_font)
            x += seg_w
            pos += len(seg)

        y += line_h + LINE_SPACING

    return img


def build_text_overlay_clips(card: dict, duration: float):
    """
    生成两个文字图层：
    1. 主文字层：白字 + 高亮橙字，淡入
    2. 高亮强调层：只对高亮词做一次轻微 pulse
    """
    text = card.get("text", "").strip()
    highlight_words = card.get("highlight", []) or []

    if not text:
        return []

    # 主文字层
    base_img = draw_multiline_text_image(
        text=text,
        highlight_words=highlight_words,
        normal_font_size=NORMAL_FONT_SIZE,
        highlight_font_size=HIGHLIGHT_FONT_SIZE,
        color_normal=NORMAL_TEXT_COLOR,
        color_highlight=HIGHLIGHT_TEXT_COLOR,
    )

    base_clip = ImageClip(pil_to_np(base_img)).set_duration(duration)
    base_clip = base_clip.set_position((0, 0)).fadein(TEXT_FADEIN_SEC)

    clips = [base_clip]

    # 高亮强调层：只有高亮词才做
    if highlight_words:
        highlight_only_img = draw_multiline_text_image(
            text=text,
            highlight_words=highlight_words,
            normal_font_size=NORMAL_FONT_SIZE,
            highlight_font_size=HIGHLIGHT_FONT_SIZE,
            color_normal=(255, 255, 255, 0),         # 普通字透明
            color_highlight=HIGHLIGHT_TEXT_COLOR,    # 只保留高亮词
        )

        h_clip = ImageClip(pil_to_np(highlight_only_img)).set_position((0, 0))
        h_clip = h_clip.set_start(HIGHLIGHT_START_SEC).set_duration(HIGHLIGHT_DURATION)
        h_clip = h_clip.resize(
            lambda t: 1 + (HIGHLIGHT_SCALE_END - 1) * min(max(t / 0.35, 0), 1)
        )

        clips.append(h_clip)

    return clips


# =========================
# 背景镜头动作
# =========================
def build_motion_clip(image_path: Path, duration: float, motion: str):
    img = ImageClip(str(image_path)).set_duration(duration)

    def center_pos(t):
        return ("center", "center")

    if motion == "zoom_in":
        def scale_func(t):
            progress = 0 if duration <= 0 else (t / duration)
            return ZOOM_IN_START + (ZOOM_IN_END - ZOOM_IN_START) * progress
        moving = img.resize(lambda t: scale_func(t)).set_position(center_pos)

    elif motion == "zoom_out":
        def scale_func(t):
            progress = 0 if duration <= 0 else (t / duration)
            return ZOOM_OUT_START + (ZOOM_OUT_END - ZOOM_OUT_START) * progress
        moving = img.resize(lambda t: scale_func(t)).set_position(center_pos)

    elif motion == "pan_left":
        moving = img.resize(1.06).set_position(
            lambda t: (
                -(PAN_DISTANCE_X * (t / duration)) if duration > 0 else 0,
                "center"
            )
        )

    elif motion == "pan_right":
        moving = img.resize(1.06).set_position(
            lambda t: (
                (PAN_DISTANCE_X * (t / duration)) if duration > 0 else 0,
                "center"
            )
        )

    elif motion == "pan_up":
        moving = img.resize(1.05).set_position(
            lambda t: (
                "center",
                -(PAN_DISTANCE_Y * (t / duration)) if duration > 0 else 0
            )
        )

    elif motion == "pan_down":
        moving = img.resize(1.05).set_position(
            lambda t: (
                "center",
                (PAN_DISTANCE_Y * (t / duration)) if duration > 0 else 0
            )
        )

    else:
        moving = img.set_position(center_pos)

    bg = make_bg(duration)

    clip = CompositeVideoClip(
        [bg, moving],
        size=(VIDEO_W, VIDEO_H)
    ).set_duration(duration)

    return clip


def make_pause_clip(duration: float):
    return ColorClip(
        size=(VIDEO_W, VIDEO_H),
        color=BG_COLOR,
        duration=duration
    )


def append_slide_timeline(prev_clip, next_clip, timeline_clips: List, direction: str):
    d = SLIDE_DURATION

    bg = ColorClip(size=(VIDEO_W, VIDEO_H), color=BG_COLOR, duration=d)

    prev_tail_start = max(prev_clip.duration - d, 0)
    prev_tail = prev_clip.subclip(prev_tail_start, prev_clip.duration)
    next_head = next_clip.subclip(0, min(d, next_clip.duration))

    if direction == "left":
        old_moving = prev_tail.set_position(lambda t: (-VIDEO_W * (t / d), 0))
        new_moving = next_head.set_position(lambda t: (VIDEO_W - VIDEO_W * (t / d), 0))
    else:
        old_moving = prev_tail.set_position(lambda t: (VIDEO_W * (t / d), 0))
        new_moving = next_head.set_position(lambda t: (-VIDEO_W + VIDEO_W * (t / d), 0))

    transition = CompositeVideoClip(
        [bg, old_moving, new_moving],
        size=(VIDEO_W, VIDEO_H)
    ).set_duration(d)

    prev_main = prev_clip.subclip(0, prev_tail_start)
    next_main = next_clip.subclip(min(d, next_clip.duration), next_clip.duration)

    timeline_clips[-1] = prev_main
    timeline_clips.append(transition)
    timeline_clips.append(next_main)

    return timeline_clips


# =========================
# 构建单卡 / 时间线
# =========================
def build_single_card_clip(bg_path: Path, card: dict, duration: float, motion: str, enable_text_overlay: bool):
    bg_clip = build_motion_clip(bg_path, duration, motion)

    if not enable_text_overlay:
        return bg_clip

    text_overlays = build_text_overlay_clips(card, duration)
    return CompositeVideoClip(
        [bg_clip] + text_overlays,
        size=(VIDEO_W, VIDEO_H)
    ).set_duration(duration)


def build_timeline(cards: List[dict], bg_dir: Path, enable_text_overlay: bool):
    if len(cards) != 5:
        raise ValueError("当前系统固定要求 5 张卡。")

    base_clips = []
    for i, card in enumerate(cards):
        bg_path = bg_dir / f"card_{i}.png"
        duration = CARD_DURATIONS[i]
        motion = CARD_MOTIONS[i]

        clip = build_single_card_clip(
            bg_path=bg_path,
            card=card,
            duration=duration,
            motion=motion,
            enable_text_overlay=enable_text_overlay
        )
        base_clips.append(clip)

    timeline_clips = [base_clips[0]]

    for i in range(4):
        prev_clip = timeline_clips[-1]
        next_clip = base_clips[i + 1]
        transition_type = TRANSITIONS[i]

        if transition_type == "crossfade":
            timeline_clips[-1] = prev_clip.crossfadeout(CROSSFADE_DURATION)
            timeline_clips.append(next_clip.crossfadein(CROSSFADE_DURATION))

        elif transition_type == "slide_left":
            timeline_clips = append_slide_timeline(
                prev_clip=timeline_clips[-1],
                next_clip=next_clip,
                timeline_clips=timeline_clips,
                direction="left"
            )

        elif transition_type == "slide_right":
            timeline_clips = append_slide_timeline(
                prev_clip=timeline_clips[-1],
                next_clip=next_clip,
                timeline_clips=timeline_clips,
                direction="right"
            )

        elif transition_type == "pause_cut":
            timeline_clips.append(make_pause_clip(PAUSE_DURATION))
            timeline_clips.append(next_clip)

        else:
            timeline_clips.append(next_clip)

    return concatenate_videoclips(timeline_clips, method="compose")


# =========================
# 音乐
# =========================
def prepare_background_music(music_path: Path, target_duration: float):
    audio = AudioFileClip(str(music_path))

    start_sec = MUSIC_START_SEC
    if start_sec >= audio.duration:
        print(f"注意：MUSIC_START_SEC={start_sec} 超过音乐长度 {audio.duration:.2f} 秒，自动改为 0。")
        start_sec = 0

    audio = audio.subclip(start_sec)

    if audio.duration < target_duration:
        audio = afx.audio_loop(audio, duration=target_duration)
    else:
        audio = audio.subclip(0, target_duration)

    audio = audio.volumex(AUDIO_VOLUME)

    if AUDIO_FADEIN_SEC > 0:
        audio = audio.audio_fadein(AUDIO_FADEIN_SEC)
    if AUDIO_FADEOUT_SEC > 0:
        audio = audio.audio_fadeout(AUDIO_FADEOUT_SEC)

    return audio


# =========================
# 主程序
# =========================
def main():
    global ENABLE_TEXT_OVERLAY

    print("开始生成知识图卡视频 v4 Pillow ...")

    data = load_script()
    cards = data.get("cards", [])
    if not cards:
        raise ValueError("script.json 中没有 cards。")

    bg_dir, enable_overlay = find_background_dir()
    ENABLE_TEXT_OVERLAY = enable_overlay

    music_path = find_music_file()

    print(f"背景目录：{bg_dir}")
    print(f"文字图层启用：{ENABLE_TEXT_OVERLAY}")
    if not ENABLE_TEXT_OVERLAY:
        print("提示：当前使用的是 images/flat/，为避免双字，已自动关闭文字叠加。")
        print("如果你想让文字真正动起来，请把纯背景图放到 images/bg_layer/card_0~4.png")

    print("镜头动作：", CARD_MOTIONS)
    print("转场配置：", TRANSITIONS)
    print("背景音乐：", music_path.name)

    video = build_timeline(cards, bg_dir, ENABLE_TEXT_OVERLAY)

    audio = prepare_background_music(music_path, video.duration)
    video = video.set_audio(audio)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"视频总时长：{video.duration:.2f} 秒")
    print("开始输出视频，请稍等...")

    video.write_videofile(
        str(OUTPUT_FILE),
        fps=FPS,
        codec="libx264",
        audio_codec="aac"
    )

    print(f"\n✅ 视频生成完成：{OUTPUT_FILE}")


if __name__ == "__main__":
    main()