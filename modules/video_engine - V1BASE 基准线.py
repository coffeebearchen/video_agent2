# -*- coding: utf-8 -*-
"""
video_engine.py

功能：
- 优先读取 scene_plan.json 的 duration
- 读取 images/flat/card_0~4.png
- 自动把所有图片统一处理为 1080x1350（竖版短视频尺寸）
- 如果有 audio/card_0~4.mp3，则可按音频时长生成视频
- 如果 scene 中定义了 duration，则优先使用 scene.duration
- 如果没有音频，也没有 scene.duration，则默认每张图 4 秒
- 输出 output/video.mp4

目标：
- 保持主链简单
- 提高 Windows 播放兼容性
- 避免因图片尺寸异常导致 ffmpeg 编码失败
- 让 scene 开始控制视频节奏
"""

import os
import json
import shutil
from PIL import Image
from moviepy.editor import ImageClip, AudioFileClip, concatenate_videoclips


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SCRIPT_FILE = os.path.join(BASE_DIR, "script.json")
SCENE_FILE_NEW = os.path.join(BASE_DIR, "data", "current", "scene_plan.json")
SCENE_FILE_OLD = os.path.join(BASE_DIR, "scene_plan.json")

IMAGES_DIR = os.path.join(BASE_DIR, "images", "flat")
AUDIO_DIR = os.path.join(BASE_DIR, "audio")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
NORMALIZED_DIR = os.path.join(OUTPUT_DIR, "normalized_images")

VIDEO_FILE = os.path.join(OUTPUT_DIR, "video.mp4")
TEMP_AUDIO_FILE = os.path.join(OUTPUT_DIR, "temp-audio.m4a")

DEFAULT_CARD_DURATION = 4.0
REQUIRED_CARD_COUNT = 5

TARGET_W = 1080
TARGET_H = 1350


def ensure_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(NORMALIZED_DIR, exist_ok=True)


def load_json_file(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到文件：{path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_scene_data():
    """
    优先级：
    1. data/current/scene_plan.json
    2. 根目录 scene_plan.json
    3. 没有则返回 None
    """
    if os.path.exists(SCENE_FILE_NEW):
        print(f"✅ 使用 scene 文件：{SCENE_FILE_NEW}")
        return load_json_file(SCENE_FILE_NEW)

    if os.path.exists(SCENE_FILE_OLD):
        print(f"✅ 使用 scene 文件：{SCENE_FILE_OLD}")
        return load_json_file(SCENE_FILE_OLD)

    print("ℹ️ 未找到 scene_plan.json，回退到 script.json")
    return None


def load_script(script_file):
    return load_json_file(script_file)


def validate_script(data):
    cards = data.get("cards", [])
    if not isinstance(cards, list):
        raise ValueError("当前系统要求 cards 为列表")
    if len(cards) != REQUIRED_CARD_COUNT:
        raise ValueError(
            f"当前系统要求 cards 数量固定为 {REQUIRED_CARD_COUNT} 条，实际为：{len(cards)}"
        )


def validate_scene(scene_data):
    scenes = scene_data.get("scenes", [])
    if not isinstance(scenes, list):
        raise ValueError("scene_plan.json 中 scenes 必须为列表")
    if len(scenes) != REQUIRED_CARD_COUNT:
        raise ValueError(
            f"当前系统要求 scenes 数量固定为 {REQUIRED_CARD_COUNT} 条，实际为：{len(scenes)}"
        )


def remove_old_output():
    for path in [VIDEO_FILE, TEMP_AUDIO_FILE]:
        if os.path.exists(path):
            try:
                os.remove(path)
                print(f"🧹 已删除旧文件：{os.path.relpath(path, BASE_DIR)}")
            except Exception as e:
                print(f"⚠️ 删除旧文件失败：{path} | {e}")

    if os.path.exists(NORMALIZED_DIR):
        try:
            shutil.rmtree(NORMALIZED_DIR)
        except Exception:
            pass
    os.makedirs(NORMALIZED_DIR, exist_ok=True)


def fit_image_to_canvas(img, target_w=TARGET_W, target_h=TARGET_H):
    """
    把任意图片处理成固定竖版画布 1080x1350
    规则：
    - 保持比例缩放
    - 居中放到白底画布上
    - 最终尺寸固定
    """
    img = img.convert("RGB")
    src_w, src_h = img.size

    if src_w <= 0 or src_h <= 0:
        raise ValueError(f"图片尺寸异常：{img.size}")

    scale = min(target_w / src_w, target_h / src_h)
    new_w = max(2, int(src_w * scale))
    new_h = max(2, int(src_h * scale))

    if new_w % 2 != 0:
        new_w -= 1
    if new_h % 2 != 0:
        new_h -= 1

    new_w = max(2, new_w)
    new_h = max(2, new_h)

    resized = img.resize((new_w, new_h), Image.LANCZOS)

    canvas = Image.new("RGB", (target_w, target_h), (255, 255, 255))
    x = (target_w - new_w) // 2
    y = (target_h - new_h) // 2
    canvas.paste(resized, (x, y))

    return canvas


def normalize_image_file(src_path, index):
    if not os.path.exists(src_path):
        raise FileNotFoundError(f"缺少图片文件：{src_path}")

    img = Image.open(src_path)
    final_img = fit_image_to_canvas(img, TARGET_W, TARGET_H)

    out_path = os.path.join(NORMALIZED_DIR, f"card_{index}.png")
    final_img.save(out_path, quality=95)

    print(
        f"🖼 已标准化图片：{os.path.relpath(src_path, BASE_DIR)} "
        f"-> {os.path.relpath(out_path, BASE_DIR)} | size={final_img.size}"
    )
    return out_path


def get_scene_duration(scene_data, index):
    """
    从 scene_plan.json 中读取 duration
    """
    if not scene_data:
        return None

    scenes = scene_data.get("scenes", [])
    if index >= len(scenes):
        return None

    value = scenes[index].get("duration", None)
    if value is None:
        return None

    try:
        value = float(value)
    except Exception:
        return None

    if value <= 0:
        return None

    return value


def build_video_clips(script_data, scene_data=None):
    clips = []

    for i, card in enumerate(script_data["cards"]):
        raw_image_file = os.path.join(IMAGES_DIR, f"card_{i}.png")
        image_file = normalize_image_file(raw_image_file, i)

        audio_file = os.path.join(AUDIO_DIR, f"card_{i}.mp3")

        if not os.path.exists(image_file):
            raise FileNotFoundError(f"标准化后图片不存在：{image_file}")

        print(f"\n[构建视频片段] Card {i}")
        print(f"image     : {os.path.relpath(image_file, BASE_DIR)}")

        scene_duration = get_scene_duration(scene_data, i)

        if os.path.exists(audio_file):
            audio_clip = AudioFileClip(audio_file)
            audio_duration = float(audio_clip.duration)

            if audio_duration <= 0:
                raise ValueError(f"音频时长异常：{audio_file}")

            if scene_duration is not None:
                duration = scene_duration
                print(f"duration  : {round(duration, 2)} (来自 scene_plan)")
            else:
                duration = audio_duration
                print(f"duration  : {round(duration, 2)} (来自音频)")

            print(f"audio_file: {os.path.relpath(audio_file, BASE_DIR)}")

            # 如果 scene.duration 比音频短，仍然至少使用音频时长，避免语音被截断
            final_duration = max(duration, audio_duration)

            if final_duration != duration:
                print(
                    f"⚠️ scene duration 小于音频时长，已自动使用音频时长：{round(final_duration, 2)}"
                )

            clip = ImageClip(image_file).set_duration(final_duration).set_audio(audio_clip)

        else:
            if scene_duration is not None:
                duration = scene_duration
                print(f"duration  : {round(duration, 2)} (来自 scene_plan)")
            else:
                duration = DEFAULT_CARD_DURATION
                print(f"duration  : {duration} (默认值)")

            print("audio_file: (无)")
            clip = ImageClip(image_file).set_duration(duration)

        clips.append(clip)

    return clips


def close_clips(clips, final_clip=None):
    for clip in clips:
        try:
            if getattr(clip, "audio", None):
                clip.audio.close()
        except Exception:
            pass

        try:
            clip.close()
        except Exception:
            pass

    if final_clip is not None:
        try:
            if getattr(final_clip, "audio", None):
                final_clip.audio.close()
        except Exception:
            pass

        try:
            final_clip.close()
        except Exception:
            pass


def main():
    ensure_dirs()

    print("=== Video Engine 开始执行 ===")

    script_data = load_script(SCRIPT_FILE)
    validate_script(script_data)

    scene_data = load_scene_data()
    if scene_data is not None:
        validate_scene(scene_data)

    remove_old_output()

    clips = []
    final_clip = None

    try:
        clips = build_video_clips(script_data, scene_data)

        print("\n=== 开始拼接视频 ===")
        print(f"输出文件：{os.path.relpath(VIDEO_FILE, BASE_DIR)}")

        final_clip = concatenate_videoclips(clips, method="compose")

        final_clip.write_videofile(
            VIDEO_FILE,
            fps=24,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=TEMP_AUDIO_FILE,
            remove_temp=True,
            ffmpeg_params=[
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart"
            ]
        )

        if not os.path.exists(VIDEO_FILE):
            raise FileNotFoundError(f"视频文件未生成：{VIDEO_FILE}")

        file_size = os.path.getsize(VIDEO_FILE)
        if file_size <= 0:
            raise ValueError(f"视频文件为空：{VIDEO_FILE}")

        print("\n=== 完成 ===")
        print(f"已生成视频：{os.path.relpath(VIDEO_FILE, BASE_DIR)}")
        print(f"文件大小：{file_size} bytes")

    finally:
        close_clips(clips, final_clip)


if __name__ == "__main__":
    main()