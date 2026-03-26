# -*- coding: utf-8 -*-

"""
snapshot_generator.py

生成当前项目运行态快照
输出：output/project_snapshot.md
"""

import os
import json
from datetime import datetime


OUTPUT_FILE = "output/project_snapshot.md"
SCRIPT_FILE = "script.json"
IMAGES_DIR = "images"
VIDEO_FILE = "output/video.mp4"

MODULES = [
    "script_generator.py",
    "image_engine.py",
    "video_engine.py",
    "run_pipeline.py"
]


def read_script_info():
    if not os.path.exists(SCRIPT_FILE):
        return None

    try:
        with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        title = data.get("title", "")
        cards = data.get("cards", [])
        schema = data.get("schema_version", "")

        return {
            "title": title,
            "cards_count": len(cards),
            "schema_version": schema
        }

    except Exception:
        return None


def list_images():
    images = []

    if os.path.exists(IMAGES_DIR):
        for name in sorted(os.listdir(IMAGES_DIR)):
            if name.lower().startswith("card_"):
                images.append(os.path.join(IMAGES_DIR, name))

    return images


def check_modules():
    status = {}

    for m in MODULES:
        status[m] = os.path.exists(m)

    return status


def generate_snapshot():

    os.makedirs("output", exist_ok=True)

    script_info = read_script_info()
    images = list_images()
    modules = check_modules()

    lines = []

    lines.append("# Project Runtime Snapshot\n")

    lines.append(f"PROJECT: Creator OS / Python Knowledge Video Engine")
    lines.append(f"VERSION: Python7")
    lines.append(f"DATE: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")

    lines.append("---\n")

    lines.append("## System Structure\n")
    lines.append("input.txt")
    lines.append("script_generator.py")
    lines.append("script.json")
    lines.append("image_engine.py")
    lines.append("video_engine.py")
    lines.append("run_pipeline.py\n")

    lines.append("---\n")

    lines.append("## Script Status\n")

    if script_info:
        lines.append(f"title: {script_info['title']}")
        lines.append(f"cards_count: {script_info['cards_count']}")
        lines.append(f"schema_version: {script_info['schema_version']}\n")
    else:
        lines.append("script.json not found\n")

    lines.append("---\n")

    lines.append("## Images\n")

    if images:
        for img in images:
            lines.append(img)
    else:
        lines.append("No images found")

    lines.append("\n---\n")

    lines.append("## Video\n")

    if os.path.exists(VIDEO_FILE):
        lines.append(VIDEO_FILE)
    else:
        lines.append("video not generated")

    lines.append("\n---\n")

    lines.append("## Modules\n")

    for m, ok in modules.items():
        lines.append(f"{m} : {'OK' if ok else 'MISSING'}")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("✅ Snapshot generated:", OUTPUT_FILE)


if __name__ == "__main__":
    generate_snapshot()