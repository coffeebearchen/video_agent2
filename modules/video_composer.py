import math
import os
from typing import List

from moviepy import ImageClip, AudioFileClip, concatenate_videoclips


def compose_video(card_paths: List[str], voice_path: str, output_dir: str, fps: int = 24) -> str:
    if not card_paths:
        raise ValueError("没有可用于合成视频的图卡。")

    if not os.path.exists(voice_path):
        raise FileNotFoundError(f"语音文件不存在: {voice_path}")

    audio = AudioFileClip(voice_path)
    total_audio_duration = audio.duration

    # 每张卡平均分配语音时长，并设置一个最低显示时长，避免切换太快
    per_card_duration = max(3.0, total_audio_duration / len(card_paths))

    clips = []
    for path in card_paths:
        clip = ImageClip(path).with_duration(per_card_duration)
        clips.append(clip)

    video = concatenate_videoclips(clips, method="compose")

    # 如果视频总长略长于音频，保留视频长度；
    # 如果音频更长，则以音频为准，确保音频不被截断。
    video = video.with_audio(audio)

    final_duration = max(video.duration, total_audio_duration)
    video = video.with_duration(final_duration)

    video_path = os.path.join(output_dir, "video.mp4")

    video.write_videofile(
        video_path,
        fps=fps,
        codec="libx264",
        audio_codec="aac"
    )

    return video_path