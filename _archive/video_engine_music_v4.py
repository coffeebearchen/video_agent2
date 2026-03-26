# video_engine_music_v4.py

import json
from pathlib import Path
from moviepy.editor import *
import numpy as np

BASE_DIR = Path(__file__).resolve().parent

IMAGES_DIR = BASE_DIR / "images" / "flat"
MUSIC_DIR = BASE_DIR / "assets" / "music"
OUTPUT_DIR = BASE_DIR / "output"
SCRIPT_FILE = BASE_DIR / "script.json"

VIDEO_W = 1080
VIDEO_H = 1350
FPS = 24

CARD_DURATION = 3

AUDIO_VOLUME = 0.22
MUSIC_START_SEC = 20

TEXT_FADE_TIME = 0.4
HIGHLIGHT_SCALE = 1.06


def load_script():
    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def create_background(card_index):

    img = ImageClip(str(IMAGES_DIR / f"card_{card_index}.png"))

    clip = img.set_duration(CARD_DURATION)

    # 轻微镜头推进
    clip = clip.resize(lambda t: 1 + 0.05 * (t / CARD_DURATION))

    bg = ColorClip((VIDEO_W, VIDEO_H), (0, 0, 0), duration=CARD_DURATION)

    return CompositeVideoClip([bg, clip.set_position("center")],
                              size=(VIDEO_W, VIDEO_H))


def create_text_layer(text, highlight_words):

    font = "Arial"

    text_clip = TextClip(
        text,
        fontsize=70,
        font=font,
        color="white",
        method="caption",
        size=(900, None),
        align="center"
    )

    text_clip = text_clip.set_position(("center", "center"))
    text_clip = text_clip.set_duration(CARD_DURATION)

    # 淡入
    text_clip = text_clip.crossfadein(TEXT_FADE_TIME)

    layers = [text_clip]

    # 高亮词
    for word in highlight_words:

        if word.strip() == "":
            continue

        highlight = TextClip(
            word,
            fontsize=72,
            font=font,
            color="#FFA500"
        )

        highlight = highlight.set_position(("center", "center"))
        highlight = highlight.set_start(0.8)
        highlight = highlight.set_duration(1)

        highlight = highlight.resize(
            lambda t: 1 + (HIGHLIGHT_SCALE - 1) * min(t / 0.5, 1)
        )

        layers.append(highlight)

    return layers


def build_video(cards):

    clips = []

    for i, card in enumerate(cards):

        bg = create_background(i)

        text_layers = create_text_layer(
            card["text"],
            card.get("highlight", [])
        )

        clip = CompositeVideoClip(
            [bg] + text_layers,
            size=(VIDEO_W, VIDEO_H)
        )

        clip = clip.set_duration(CARD_DURATION)

        clips.append(clip)

    final = concatenate_videoclips(clips, method="compose")

    return final


def load_music(duration):

    files = list(MUSIC_DIR.glob("*.mp3"))

    if not files:
        return None

    music = AudioFileClip(str(files[0]))

    music = music.subclip(MUSIC_START_SEC)

    if music.duration < duration:
        music = afx.audio_loop(music, duration=duration)

    music = music.subclip(0, duration)

    music = music.volumex(AUDIO_VOLUME)

    return music


def main():

    data = load_script()

    cards = data["cards"]

    video = build_video(cards)

    music = load_music(video.duration)

    if music:
        video = video.set_audio(music)

    OUTPUT_DIR.mkdir(exist_ok=True)

    out = OUTPUT_DIR / "video.mp4"

    video.write_videofile(
        str(out),
        fps=FPS,
        codec="libx264",
        audio_codec="aac"
    )


if __name__ == "__main__":
    main()