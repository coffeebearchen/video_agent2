# -*- coding: utf-8 -*-
"""
web_capture_to_cards_v2.py

【卡图生成模块】

作用：
1. 读取 capture_path
2. 读取 page_portrait_4x5.png
3. 切分为5张卡图

注意：
- 若缺截图，直接报错
"""

import os
from PIL import Image
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CURRENT_CAPTURE_PATH_FILE = BASE_DIR / "current_capture_path.txt"
OUTPUT_DIR = BASE_DIR / "images" / "flat"


def get_capture_path():
    if not CURRENT_CAPTURE_PATH_FILE.exists():
        raise RuntimeError("❌ 找不到 capture_path")

    return Path(CURRENT_CAPTURE_PATH_FILE.read_text().strip())


def main():
    capture_path = get_capture_path()

    img_path = capture_path / "page_portrait_4x5.png"

    if not img_path.exists():
        raise RuntimeError("❌ 缺少 page_portrait_4x5.png，请检查 Step 1")

    img = Image.open(img_path)

    w, h = img.size

    regions = [
        (0, 0, w, int(0.2*h)),
        (0, int(0.2*h), w, int(0.4*h)),
        (0, int(0.4*h), w, int(0.6*h)),
        (0, int(0.6*h), w, int(0.8*h)),
        (0, int(0.8*h), w, h),
    ]

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for i, box in enumerate(regions):
        crop = img.crop(box)
        path = OUTPUT_DIR / f"card_{i}.png"
        crop.save(path)
        print(f"✅ 已生成：{path}")

    print("✅ 卡图生成完成")


if __name__ == "__main__":
    main()