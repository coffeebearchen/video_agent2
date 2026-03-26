# video_engine_layers_v1.py
# -*- coding: utf-8 -*-

"""
高级分层视频引擎 v1

说明：
1. 直接读取 images/layers/ 中的分层素材
2. 支持层：
   - card_x_bg
   - card_x_overlay
   - card_x_text
   - card_x_meta（可选）
3. 支持：
   - 背景轻微流动
   - 文字淡入
   - 文字轻微上浮
   - 可选 meta 淡入
   - 转场
   - 背景音乐

运行：
python video_engine_layers_v1.py
"""

from pathlib import Path
from typing import Optional, List

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

LAYERS_DIR = BASE_DIR / "images" / "layers"
MUSIC_DIR = BASE_DIR / "assets" / "music"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_FILE = OUTPUT_DIR / "video.mp4"

# =========================
# 输出契约（冻结）
# =========================
VIDEO_W = 1080
VIDEO_H = 1350
FPS = 24

# =========================
# 图卡固定时长（秒）
# hook / concept / analogy / example / insight
# =========================
CARD_DURATIONS = [2.6, 3.0, 3.2, 3.2, 2.8]

# =========================
# 背景层动作
# 可选：
# zoom_in / zoom_out / pan_left / pan_right / pan_up / pan_down / static
# =========================
BG_MOTIONS = [
    "zoom_in",    # card_0
    "pan_left",   # card_1
    "zoom_out",   # card_2
    "pan_right",  # card_3
    "zoom_in",    # card_4
]

# =========================
# 转场配置（共 4 段）
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
# 背景运动参数
# =========================
ZOOM_IN_START = 1.00
ZOOM_IN_END = 1.08

ZOOM_OUT_START = 1.08
ZOOM_OUT_END = 1.00

PAN_DISTANCE_X = 60
PAN_DISTANCE_Y = 50

# =========================
# 文字层时间轴
# =========================
TEXT_START_SEC = 0.18
TEXT_FADEIN_SEC = 0.35
TEXT_FLOAT_UP_PIXELS = 10
TEXT_FLOAT_TOTAL_SEC = 1.2

# overlay 层
OVERLAY_START_SEC = 0.00
OVERLAY_FADEIN_SEC = 0.20

# meta 层（可选）
ENABLE_META_LAYER = True
META_START_SEC = 0.95
META_FADEIN_SEC = 0.35

# =========================
# 音乐参数
# =========================
AUDIO_VOLUME = 0.22
MUSIC_START_SEC = 20
AUDIO_FADEIN_SEC = 0.6
AUDIO_FADEOUT_SEC = 0.8

BG_COLOR = (0, 0, 0)

SUPPORTED_EXTS = [".png", ".jpg", ".jpeg", ".webp"]


# =========================
# 文件查找
# =========================
def find_layer_file(card_index: int, layer_name: str) -> Optional[Path]:
    """
    查找例如：
    card_0_bg.png
    card_0_overlay.png
    card_0_text.png
    card_0_meta.png

    会自动尝试多种扩展名。
    """
    for ext in SUPPORTED_EXTS:
        p = LAYERS_DIR / f"card_{card_index}_{layer_name}{ext}"
        if p.exists():
            return p

    # 再做一次宽松匹配，兼容可能出现的额外命名
    pattern = f"card_{card_index}_{layer_name}*"
    matches = sorted([p for p in LAYERS_DIR.glob(pattern) if p.is_file()])
    if matches:
        return matches[0]

    return None


def ensure_required_layers():
    if not LAYERS_DIR.exists():
        raise FileNotFoundError(f"未找到目录：{LAYERS_DIR}")

    for i in range(5):
        bg = find_layer_file(i, "bg")
        overlay = find_layer_file(i, "overlay")
        text = find_layer_file(i, "text")

        if bg is None:
            raise FileNotFoundError(f"缺少背景层：card_{i}_bg")
        if overlay is None:
            raise FileNotFoundError(f"缺少 overlay 层：card_{i}_overlay")
        if text is None:
            raise FileNotFoundError(f"缺少文字层：card_{i}_text")


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


# =========================
# 基础层
# =========================
def make_bg(duration: float):
    return ColorClip(
        size=(VIDEO_W, VIDEO_H),
        color=BG_COLOR,
        duration=duration
    )


def build_motion_bg_clip(image_path: Path, duration: float, motion: str):
    """
    背景层镜头流动
    """
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


def build_overlay_clip(image_path: Path, duration: float):
    """
    overlay 层：底板/遮罩层
    """
    clip = ImageClip(str(image_path)).set_duration(duration)
    clip = clip.set_start(OVERLAY_START_SEC)
    clip = clip.fadein(OVERLAY_FADEIN_SEC)
    clip = clip.set_position(("center", "center"))
    return clip


def build_text_clip(image_path: Path, duration: float):
    """
    文字层：淡入 + 轻微上浮
    说明：
    - 这里直接使用你现有的 text 图层图片
    - 所以不需要重新排字
    """
    visible_duration = max(duration - TEXT_START_SEC, 0.1)

    clip = ImageClip(str(image_path)).set_duration(visible_duration)
    clip = clip.set_start(TEXT_START_SEC)
    clip = clip.fadein(TEXT_FADEIN_SEC)

    # 轻微上浮，制造“文字在呼吸”的感觉
    def pos_func(t):
        if TEXT_FLOAT_TOTAL_SEC <= 0:
            dy = 0
        else:
            progress = min(max(t / TEXT_FLOAT_TOTAL_SEC, 0), 1)
            dy = -TEXT_FLOAT_UP_PIXELS * progress
        return ("center", dy)

    clip = clip.set_position(pos_func)
    return clip


def build_meta_clip(image_path: Path, duration: float):
    """
    meta 层：可选
    通常比较淡，不抢主体
    """
    visible_duration = max(duration - META_START_SEC, 0.1)

    clip = ImageClip(str(image_path)).set_duration(visible_duration)
    clip = clip.set_start(META_START_SEC)
    clip = clip.fadein(META_FADEIN_SEC)
    clip = clip.set_position(("center", "center"))
    return clip


# =========================
# 单卡组合
# =========================
def build_single_card_clip(card_index: int, duration: float, bg_motion: str):
    bg_path = find_layer_file(card_index, "bg")
    overlay_path = find_layer_file(card_index, "overlay")
    text_path = find_layer_file(card_index, "text")
    meta_path = find_layer_file(card_index, "meta")

    if bg_path is None or overlay_path is None or text_path is None:
        raise FileNotFoundError(f"card_{card_index} 分层文件不完整。")

    bg_clip = build_motion_bg_clip(bg_path, duration, bg_motion)
    overlay_clip = build_overlay_clip(overlay_path, duration)
    text_clip = build_text_clip(text_path, duration)

    layers = [bg_clip, overlay_clip, text_clip]

    if ENABLE_META_LAYER and meta_path is not None:
        meta_clip = build_meta_clip(meta_path, duration)
        layers.append(meta_clip)

    card_clip = CompositeVideoClip(
        layers,
        size=(VIDEO_W, VIDEO_H)
    ).set_duration(duration)

    return card_clip


# =========================
# 转场
# =========================
def make_pause_clip(duration: float):
    return ColorClip(
        size=(VIDEO_W, VIDEO_H),
        color=BG_COLOR,
        duration=duration
    )


def append_slide_timeline(prev_clip, next_clip, timeline_clips: List, direction: str):
    """
    左右轻推：
    - left：旧画面向左，新画面从右进
    - right：旧画面向右，新画面从左进
    """
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


def build_timeline():
    base_clips = []
    for i in range(5):
        clip = build_single_card_clip(
            card_index=i,
            duration=CARD_DURATIONS[i],
            bg_motion=BG_MOTIONS[i]
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
    print("开始生成高级分层视频 v1 ...")

    ensure_required_layers()
    music_path = find_music_file()

    print(f"分层目录：{LAYERS_DIR}")
    print("背景动作：", BG_MOTIONS)
    print("转场配置：", TRANSITIONS)
    print("背景音乐：", music_path.name)

    for i in range(5):
        print(
            f"card_{i}:",
            "bg =", find_layer_file(i, "bg").name if find_layer_file(i, "bg") else "None",
            "| overlay =", find_layer_file(i, "overlay").name if find_layer_file(i, "overlay") else "None",
            "| text =", find_layer_file(i, "text").name if find_layer_file(i, "text") else "None",
            "| meta =", find_layer_file(i, "meta").name if find_layer_file(i, "meta") else "None",
        )

    video = build_timeline()
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