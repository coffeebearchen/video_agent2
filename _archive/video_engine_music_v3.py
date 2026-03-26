# video_engine_music_v3.py
# -*- coding: utf-8 -*-

"""
知识图卡视频引擎 v3
目标：
1. 让静态图有更强的“流动感”
2. 支持多种镜头动作：
   - zoom_in
   - zoom_out
   - pan_left
   - pan_right
   - pan_up
   - pan_down
   - static
3. 支持转场：
   - crossfade
   - slide_left
   - slide_right
   - pause_cut
4. 支持背景音乐
5. 保持 1080x1350 / 4:5 输出契约不变

运行方式：
python video_engine_music_v3.py
"""

from pathlib import Path
from typing import List

from moviepy.editor import (
    ImageClip,
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    concatenate_videoclips,
    afx,
)

# =========================
# 路径配置
# =========================
BASE_DIR = Path(__file__).resolve().parent

IMAGES_DIR = BASE_DIR / "images" / "flat"
MUSIC_DIR = BASE_DIR / "assets" / "music"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_FILE = OUTPUT_DIR / "video.mp4"

# =========================
# 冻结的视频画布契约
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
# 每张卡的镜头动作
# 可选：
# "zoom_in"
# "zoom_out"
# "pan_left"
# "pan_right"
# "pan_up"
# "pan_down"
# "static"
# =========================
CARD_MOTIONS = [
    "zoom_in",    # card_0
    "pan_left",   # card_1
    "zoom_out",   # card_2
    "pan_right",  # card_3
    "zoom_in",    # card_4
]

# =========================
# 转场配置（共4段）
# 0->1, 1->2, 2->3, 3->4
# 可选：
# "crossfade"
# "slide_left"
# "slide_right"
# "pause_cut"
# =========================
TRANSITIONS = [
    "crossfade",
    "slide_left",
    "pause_cut",
    "crossfade",
]

# =========================
# 转场时长
# =========================
CROSSFADE_DURATION = 0.45
SLIDE_DURATION = 0.42
PAUSE_DURATION = 0.18

# =========================
# 缩放参数
# 不要太大，知识类视频要克制
# =========================
ZOOM_IN_START = 1.00
ZOOM_IN_END = 1.08

ZOOM_OUT_START = 1.08
ZOOM_OUT_END = 1.00

# =========================
# 平移参数（像素）
# 不要太大，避免“飘”
# =========================
PAN_DISTANCE_X = 60
PAN_DISTANCE_Y = 50

# =========================
# 背景音乐参数
# =========================
AUDIO_VOLUME = 0.22
MUSIC_START_SEC = 20
AUDIO_FADEIN_SEC = 0.6
AUDIO_FADEOUT_SEC = 0.8

BG_COLOR = (0, 0, 0)


def find_card_images() -> List[Path]:
    image_paths = []
    for i in range(5):
        path = IMAGES_DIR / f"card_{i}.png"
        if not path.exists():
            raise FileNotFoundError(f"未找到图卡文件：{path}")
        image_paths.append(path)
    return image_paths


def find_first_music_file() -> Path:
    if not MUSIC_DIR.exists():
        raise FileNotFoundError(f"未找到音乐目录：{MUSIC_DIR}")

    preferred_names = [
        "bgm_test.mp3",
        "bgm_test.wav",
        "bgm_test.m4a",
    ]

    for name in preferred_names:
        p = MUSIC_DIR / name
        if p.exists():
            return p

    candidates = []
    for ext in ["*.mp3", "*.wav", "*.m4a"]:
        candidates.extend(MUSIC_DIR.glob(ext))

    if not candidates:
        raise FileNotFoundError(
            f"在 {MUSIC_DIR} 中没有找到音乐文件。请至少放入一条 .mp3 / .wav / .m4a。"
        )

    return sorted(candidates)[0]


def make_bg(duration: float):
    return ColorClip(
        size=(VIDEO_W, VIDEO_H),
        color=BG_COLOR,
        duration=duration
    )


def build_motion_clip(image_path: Path, duration: float, motion: str):
    """
    根据 motion 构建单张图卡的镜头运动。
    做法：
    - 先把图做成 ImageClip
    - 再加 resize / set_position 的时间函数
    - 最后合成到固定 1080x1350 黑底画布里
    """

    img = ImageClip(str(image_path)).set_duration(duration)

    # 默认中心位置
    def center_pos(t):
        return ("center", "center")

    # 1）static
    if motion == "static":
        moving = img.set_position(center_pos)

    # 2）zoom_in
    elif motion == "zoom_in":
        def scale_func(t):
            progress = 0 if duration <= 0 else (t / duration)
            return ZOOM_IN_START + (ZOOM_IN_END - ZOOM_IN_START) * progress

        moving = img.resize(lambda t: scale_func(t)).set_position(center_pos)

    # 3）zoom_out
    elif motion == "zoom_out":
        def scale_func(t):
            progress = 0 if duration <= 0 else (t / duration)
            return ZOOM_OUT_START + (ZOOM_OUT_END - ZOOM_OUT_START) * progress

        moving = img.resize(lambda t: scale_func(t)).set_position(center_pos)

    # 4）pan_left
    elif motion == "pan_left":
        # 从稍微偏右，慢慢向左移动
        moving = img.resize(1.06).set_position(
            lambda t: (
                - (PAN_DISTANCE_X * (t / duration)) if duration > 0 else 0,
                "center"
            )
        )

    # 5）pan_right
    elif motion == "pan_right":
        # 从稍微偏左，慢慢向右移动
        moving = img.resize(1.06).set_position(
            lambda t: (
                PAN_DISTANCE_X * (t / duration) if duration > 0 else 0,
                "center"
            )
        )

    # 6）pan_up
    elif motion == "pan_up":
        moving = img.resize(1.05).set_position(
            lambda t: (
                "center",
                - (PAN_DISTANCE_Y * (t / duration)) if duration > 0 else 0
            )
        )

    # 7）pan_down
    elif motion == "pan_down":
        moving = img.resize(1.05).set_position(
            lambda t: (
                "center",
                PAN_DISTANCE_Y * (t / duration) if duration > 0 else 0
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
    """
    左右轻推：
    direction:
    - left  : 旧画面向左，新画面从右进
    - right : 旧画面向右，新画面从左进
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


def build_timeline(image_paths: List[Path]):
    if len(image_paths) != 5:
        raise ValueError("当前系统固定要求 5 张图卡。")

    base_clips = []
    for i, image_path in enumerate(image_paths):
        clip = build_motion_clip(
            image_path=image_path,
            duration=CARD_DURATIONS[i],
            motion=CARD_MOTIONS[i]
        )
        base_clips.append(clip)

    timeline_clips = [base_clips[0]]

    for i in range(4):
        prev_clip = timeline_clips[-1]
        next_base = base_clips[i + 1]
        transition_type = TRANSITIONS[i]

        if transition_type == "crossfade":
            timeline_clips[-1] = prev_clip.crossfadeout(CROSSFADE_DURATION)
            timeline_clips.append(next_base.crossfadein(CROSSFADE_DURATION))

        elif transition_type == "slide_left":
            prev_for_slide = timeline_clips[-1]
            timeline_clips = append_slide_timeline(
                prev_clip=prev_for_slide,
                next_clip=next_base,
                timeline_clips=timeline_clips,
                direction="left"
            )

        elif transition_type == "slide_right":
            prev_for_slide = timeline_clips[-1]
            timeline_clips = append_slide_timeline(
                prev_clip=prev_for_slide,
                next_clip=next_base,
                timeline_clips=timeline_clips,
                direction="right"
            )

        elif transition_type == "pause_cut":
            pause_clip = make_pause_clip(PAUSE_DURATION)
            timeline_clips.append(pause_clip)
            timeline_clips.append(next_base)

        else:
            timeline_clips.append(next_base)

    final_video = concatenate_videoclips(timeline_clips, method="compose")
    return final_video


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


def main():
    print("开始生成知识图卡视频 v3 ...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    image_paths = find_card_images()
    music_path = find_first_music_file()

    print("图卡文件：")
    for p in image_paths:
        print(" -", p.name)

    print("背景音乐：", music_path.name)
    print("镜头动作：", CARD_MOTIONS)
    print("转场配置：", TRANSITIONS)

    video = build_timeline(image_paths)

    audio = prepare_background_music(music_path, video.duration)
    video = video.set_audio(audio)

    print(f"视频总时长：{video.duration:.2f} 秒")
    print(f"音乐起始位置：{MUSIC_START_SEC} 秒")
    print(f"音乐音量：{AUDIO_VOLUME}")
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