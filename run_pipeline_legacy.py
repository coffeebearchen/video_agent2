# -*- coding: utf-8 -*-

import os
import json
import glob
import subprocess
import importlib

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_FILE = os.path.join(BASE_DIR, "script.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
VIDEO_FILE = os.path.join(OUTPUT_DIR, "video.mp4")


def load_script():
    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def clear_old_images():
    images_dir = os.path.join(BASE_DIR, "images", "flat")
    for f in glob.glob(os.path.join(images_dir, "card_*.png")):
        try:
            os.remove(f)
        except Exception:
            pass


def generate_images(data):
    print("🖼 Step 3：生成图卡")

    image_engine = importlib.import_module("image_engine")

    if not hasattr(image_engine, "generate_images"):
        raise RuntimeError("image_engine.py 中未找到 generate_images()")

    try:
        # 先尝试新接口
        image_engine.generate_images(data)
    except TypeError:
        # 回退旧接口
        image_engine.generate_images()


def generate_audio(data):
    print("🔊 Step 4：生成语音")
    from tts_engine_main import generate_all_tts
    generate_all_tts(data["cards"])


def run_video_engine():
    print("🎬 Step 5：合成视频")

    result = subprocess.run(
        ["python", "video_engine.py"],
        cwd=BASE_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    if result.returncode != 0:
        raise RuntimeError("video_engine 执行失败")


def main():
    print("\n==============================")
    print("🚀 视频生成流程开始")
    print("==============================\n")

    print("📄 Step 1：读取脚本")
    data = load_script()

    print("🧹 Step 2：清理旧图片")
    clear_old_images()

    generate_images(data)
    generate_audio(data)
    run_video_engine()

    print("\n✅ 完成！")
    print("📦 输出文件：output/video.mp4\n")


if __name__ == "__main__":
    main()