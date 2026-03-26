# video_engine_music_v2.py
# -*- coding: utf-8 -*-

"""
知识图卡视频引擎 v2
支持：
1. 淡入淡出
2. 轻微放大（Ken Burns）
3. 左右轻推
4. 短停顿切换
5. 背景音乐
6. 固定 5 张图卡输出

运行方式：
python video_engine_music_v2.py
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
# 视频画布契约（保持冻结）
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
# 每张卡的场景动作
# 可选：
# "zoom_in"   轻微放大
# "static"    静止
# =========================
CARD_MOTIONS = [
    "zoom_in",  # card_0
    "static",   # card_1
    "zoom_in",  # card_2
    "static",   # card_3
    "zoom_in",  # card_4
]

# =========================
# 卡片之间的转场类型（共 4 个）
# 0->1, 1->2, 2->3, 3->4
#
# 可选：
# "crossfade"   淡入淡出
# "slide_left"  左推
# "slide_right" 右推
# "pause_cut"   短停顿切换
# =========================
TRANSITIONS = [
    "crossfade",   # card_0 -> card_1
    "slide_left",  # card_1 -> card_2
    "pause_cut",   # card_2 -> card_3
    "crossfade",   # card_3 -> card_4
]

# =========================
# 转场时长（秒）
# =========================
CROSSFADE_DURATION = 0.45
SLIDE_DURATION = 0.42
PAUSE_DURATION = 0.18

# =========================
# 缩放参数
# 轻微放大，不可太明显
# =========================
ZOOM_START = 1.00
ZOOM_END = 1.06

# =========================
# 背景音乐参数
# =========================
AUDIO_VOLUME = 0.22
MUSIC_START_SEC = 20
AUDIO_FADEIN_SEC = 0.6
AUDIO_FADEOUT_SEC = 0.8

# =========================
# 背景色（用于 slide / black pause）
# =========================
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


def build_base_image_clip(image_path: Path, duration: float, motion: str):
    """
    构建单张图卡 clip
    支持：
    - static
    - zoom_in
    """
    clip = ImageClip(str(image_path)).set_duration(duration)

    if motion == "zoom_in":
        # 轻微慢放大，中心保持中间
        def zoom_func(t):
            if duration <= 0:
                return ZOOM_START
            progress = t / duration
            return ZOOM_START + (ZOOM_END - ZOOM_START) * progress

        clip = clip.resize(lambda t: zoom_func(t)).set_position("center")
    else:
        clip = clip.set_position("center")

    # 保底放到固定画布中，防止任何边界异常
    bg = ColorClip(size=(VIDEO_W, VIDEO_H), color=BG_COLOR, duration=duration)
    composed = CompositeVideoClip(
        [bg, clip.set_position("center")],
        size=(VIDEO_W, VIDEO_H)
    ).set_duration(duration)

    return composed


def make_pause_clip(duration: float):
    return ColorClip(
        size=(VIDEO_W, VIDEO_H),
        color=BG_COLOR,
        duration=duration
    )


def append_crossfade_timeline(base_clips: List, next_clip, timeline_clips: List):
    """
    淡入淡出：
    - 当前 clip 尾部淡出
    - 下一个 clip 头部淡入
    - 两者重叠
    """
    timeline_clips.append(
        next_clip.crossfadein(CROSSFADE_DURATION)
    )
    return timeline_clips


def append_slide_timeline(prev_clip, next_clip, timeline_clips: List, direction: str):
    """
    左右轻推：
    direction:
    - left  : 旧画面向左，新画面从右进
    - right : 旧画面向右，新画面从左进
    """
    # 为了实现 slide，这里返回一个 transition composite
    d = SLIDE_DURATION

    bg = ColorClip(size=(VIDEO_W, VIDEO_H), color=BG_COLOR, duration=d)

    if direction == "left":
        old_moving = prev_clip.subclip(max(prev_clip.duration - d, 0), prev_clip.duration).set_position(
            lambda t: (-VIDEO_W * (t / d), 0)
        )
        new_moving = next_clip.subclip(0, d).set_position(
            lambda t: (VIDEO_W - VIDEO_W * (t / d), 0)
        )
    else:
        old_moving = prev_clip.subclip(max(prev_clip.duration - d, 0), prev_clip.duration).set_position(
            lambda t: (VIDEO_W * (t / d), 0)
        )
        new_moving = next_clip.subclip(0, d).set_position(
            lambda t: (-VIDEO_W + VIDEO_W * (t / d), 0)
        )

    transition = CompositeVideoClip(
        [bg, old_moving, new_moving],
        size=(VIDEO_W, VIDEO_H)
    ).set_duration(d)

    # 时间线拆法：
    # 1) 前一个 clip 去掉尾部 d
    # 2) 插入过渡 transition
    # 3) 下一个 clip 去掉头部 d
    prev_main = prev_clip.subclip(0, max(prev_clip.duration - d, 0))
    next_main = next_clip.subclip(min(d, next_clip.duration), next_clip.duration)

    # 替换 timeline 末尾那个 prev
    timeline_clips[-1] = prev_main
    timeline_clips.append(transition)
    timeline_clips.append(next_main)

    return timeline_clips


def build_timeline(image_paths: List[Path]):
    """
    构建完整时间线：
    - 每张卡的 motion
    - 每段之间的 transition
    """
    if len(image_paths) != 5:
        raise ValueError("当前系统固定要求 5 张图卡。")

    base_clips = []
    for i, image_path in enumerate(image_paths):
        clip = build_base_image_clip(
            image_path=image_path,
            duration=CARD_DURATIONS[i],
            motion=CARD_MOTIONS[i]
        )
        base_clips.append(clip)

    # 先放第一张
    timeline_clips = [base_clips[0]]

    for i in range(4):
        prev_clip = timeline_clips[-1]
        next_base = base_clips[i + 1]
        transition_type = TRANSITIONS[i]

        if transition_type == "crossfade":
            # 对 crossfade，要对 timeline 末尾 clip 也做尾部淡出
            # 这里把 prev 替换为带淡出的版本，再 append 带淡入的新 clip
            timeline_clips[-1] = prev_clip.crossfadeout(CROSSFADE_DURATION)
            timeline_clips.append(next_base.crossfadein(CROSSFADE_DURATION))

        elif transition_type == "slide_left":
            # 这里 slide 需要用原始上一段 clip，不用已经 crossfadeout 后的那种
            # 为避免叠加复杂问题，直接重新用 base_clips[i] 构造本段
            if i == 0:
                prev_for_slide = base_clips[i]
                timeline_clips[-1] = prev_for_slide
            else:
                # 如果前面已经带 transition，为保证稳，我们用当前时间线最后一段作为 prev
                prev_for_slide = timeline_clips[-1]

            timeline_clips = append_slide_timeline(
                prev_clip=prev_for_slide,
                next_clip=next_base,
                timeline_clips=timeline_clips,
                direction="left"
            )

        elif transition_type == "slide_right":
            if i == 0:
                prev_for_slide = base_clips[i]
                timeline_clips[-1] = prev_for_slide
            else:
                prev_for_slide = timeline_clips[-1]

            timeline_clips = append_slide_timeline(
                prev_clip=prev_for_slide,
                next_clip=next_base,
                timeline_clips=timeline_clips,
                direction="right"
            )

        elif transition_type == "pause_cut":
            # 先补一小段停顿，再切到下一张
            pause_clip = make_pause_clip(PAUSE_DURATION)
            timeline_clips.append(pause_clip)
            timeline_clips.append(next_base)

        else:
            # 未知转场，默认直接切
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
    print("开始生成知识图卡视频 v2 ...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    image_paths = find_card_images()
    music_path = find_first_music_file()

    print("图卡文件：")
    for p in image_paths:
        print(" -", p.name)

    print("背景音乐：", music_path.name)
    print("卡片动作：", CARD_MOTIONS)
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