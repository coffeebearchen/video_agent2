# video_engine_music.py
# -*- coding: utf-8 -*-

"""
纯音乐图卡视频引擎（增强版）

功能：
1. 读取 images/flat/card_0.png ~ card_4.png
2. 按固定时长拼接为视频
3. 自动读取 assets/music/ 目录中的一条背景音乐
4. 可从音乐中间指定位置开始截取，跳过前奏
5. 背景音乐自动裁剪或循环到视频总时长
6. 输出 output/video.mp4

运行方式：
python video_engine_music.py
"""

from pathlib import Path

from moviepy.editor import (
    ImageClip,
    AudioFileClip,
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
# 固定图卡时长（秒）
# hook / concept / analogy / example / insight
# =========================
CARD_DURATIONS = [2.6, 3.0, 3.2, 3.2, 2.8]

# =========================
# 视频与音乐参数
# =========================
FPS = 24

# 背景音乐音量
# 原来太小，现在调大一些
# 可选建议：
# 0.18 = 稍明显
# 0.22 = 比较明显
# 0.26 = 偏大
AUDIO_VOLUME = 0.22

# 从音乐第几秒开始截取
# 用来跳过前奏
# 例如：
# 0   = 从头开始
# 10  = 从第10秒开始
# 20  = 从第20秒开始
# 30  = 从第30秒开始
MUSIC_START_SEC = 20

# 是否做淡入淡出（让音乐更柔和）
AUDIO_FADEIN_SEC = 0.6
AUDIO_FADEOUT_SEC = 0.8


def find_card_images():
    """
    固定读取 card_0.png ~ card_4.png
    """
    image_paths = []
    for i in range(5):
        path = IMAGES_DIR / f"card_{i}.png"
        if not path.exists():
            raise FileNotFoundError(f"未找到图卡文件：{path}")
        image_paths.append(path)
    return image_paths


def find_first_music_file():
    """
    从 assets/music 里找到第一条可用音乐
    支持 mp3 / wav / m4a
    优先顺序：bgm_test.mp3 / bgm_test.wav / bgm_test.m4a / 其他音频
    """
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
            f"在 {MUSIC_DIR} 中没有找到音乐文件。请确认至少有一条 .mp3 / .wav / .m4a 音乐。"
        )

    candidates = sorted(candidates)
    return candidates[0]


def build_video_clips(image_paths):
    """
    根据固定时长生成图卡 clip
    """
    clips = []

    for i, image_path in enumerate(image_paths):
        duration = CARD_DURATIONS[i]
        clip = ImageClip(str(image_path)).set_duration(duration)
        clips.append(clip)

    video = concatenate_videoclips(clips, method="compose")
    return video


def prepare_background_music(music_path, target_duration):
    """
    处理背景音乐：
    1. 从指定位置开始截取（跳过前奏）
    2. 如果不够长则循环
    3. 裁剪到与视频同长
    4. 调整音量
    5. 做淡入淡出
    """
    audio = AudioFileClip(str(music_path))

    # 如果设置的开始位置超出音乐长度，自动回退到 0
    start_sec = MUSIC_START_SEC
    if start_sec >= audio.duration:
        print(f"注意：MUSIC_START_SEC={start_sec} 超过音乐长度 {audio.duration:.2f} 秒，自动改为 0。")
        start_sec = 0

    # 先从中间截起
    audio = audio.subclip(start_sec)

    # 不够长就循环
    if audio.duration < target_duration:
        audio = afx.audio_loop(audio, duration=target_duration)
    else:
        audio = audio.subclip(0, target_duration)

    # 音量调大
    audio = audio.volumex(AUDIO_VOLUME)

    # 淡入淡出
    if AUDIO_FADEIN_SEC > 0:
        audio = audio.audio_fadein(AUDIO_FADEIN_SEC)

    if AUDIO_FADEOUT_SEC > 0:
        audio = audio.audio_fadeout(AUDIO_FADEOUT_SEC)

    return audio


def main():
    print("开始生成纯音乐图卡视频...")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    image_paths = find_card_images()
    music_path = find_first_music_file()

    print("图卡文件：")
    for p in image_paths:
        print(" -", p.name)

    print("背景音乐：", music_path.name)

    video = build_video_clips(image_paths)
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