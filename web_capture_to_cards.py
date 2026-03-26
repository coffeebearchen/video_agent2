# -*- coding: utf-8 -*-
"""
web_capture_to_cards_v2.py

精准截图版本（V2）
目标：
1. 不再简单平均裁切
2. 按“网页阅读结构”裁成 5 张图
3. 提升画面与文案的匹配感

输入：
assets/web_capture/.../page_portrait_4x5.png

输出：
images/flat/card_0.png ~ card_4.png

新增：
- 优先读取 data/current/capture_path.txt
- 若没有，再回退到“最新目录”
"""

import os
from PIL import Image


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 输入截图（你现在已有）
CAPTURE_DIR = os.path.join(BASE_DIR, "assets", "web_capture")
CAPTURE_PATH_FILE = os.path.join(BASE_DIR, "data", "current", "capture_path.txt")

# 输出图卡目录（沿用旧主链）
OUTPUT_DIR = os.path.join(BASE_DIR, "images", "flat")


def find_latest_capture():
    """找到最新截图目录"""
    if not os.path.exists(CAPTURE_DIR):
        raise FileNotFoundError("未找到 web_capture 目录")

    folders = [
        os.path.join(CAPTURE_DIR, d)
        for d in os.listdir(CAPTURE_DIR)
        if os.path.isdir(os.path.join(CAPTURE_DIR, d))
    ]

    if not folders:
        raise ValueError("web_capture 目录为空")

    latest = sorted(folders)[-1]
    return latest


def get_capture_path():
    """
    优先读取锁定的 capture_path。
    若没有，再回退到旧逻辑：找最新目录。
    """
    if os.path.exists(CAPTURE_PATH_FILE):
        with open(CAPTURE_PATH_FILE, "r", encoding="utf-8") as f:
            locked_path = f.read().strip()
        if locked_path:
            print(f"📌 使用锁定 capture_path：{locked_path}")
            if os.path.isdir(locked_path):
                return locked_path
            print("⚠️ capture_path.txt 存在，但目录不存在，回退到最新目录")

    print("⚠️ 未找到有效 capture_path.txt，回退到最新目录")
    return find_latest_capture()


def load_main_image(capture_path):
    img_path = os.path.join(capture_path, "page_portrait_4x5.png")

    if not os.path.exists(img_path):
        raise FileNotFoundError(f"未找到截图：{img_path}")

    return Image.open(img_path)


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def crop_by_structure(img):
    """
    核心逻辑：按“阅读结构”裁图
    """

    w, h = img.size

    # 👉 不再平均切，而是按结构比例
    regions = [
        # 标题区（上部）
        (0, int(0.00 * h), w, int(0.18 * h)),

        # 标题+首图
        (0, int(0.10 * h), w, int(0.35 * h)),

        # 正文前段
        (0, int(0.30 * h), w, int(0.60 * h)),

        # 正文中段
        (0, int(0.55 * h), w, int(0.82 * h)),

        # 结尾区
        (0, int(0.78 * h), w, int(1.00 * h)),
    ]

    return regions


def save_cards(img, regions):
    ensure_output_dir()

    output_files = []

    for i, box in enumerate(regions):
        crop = img.crop(box)

        out_path = os.path.join(OUTPUT_DIR, f"card_{i}.png")
        crop.save(out_path)

        print(f"✅ 已生成：{out_path}")
        output_files.append(out_path)

    return output_files


def main():
    print("=" * 70)
    print("V2 精准截图模式启动")
    print("=" * 70)

    capture_path = get_capture_path()
    print(f"使用截图目录：{capture_path}")

    img = load_main_image(capture_path)
    print(f"图片尺寸：{img.size}")

    regions = crop_by_structure(img)

    print("裁切区域：")
    for i, r in enumerate(regions):
        print(f"Card {i}: {r}")

    files = save_cards(img, regions)

    print("=" * 70)
    print("生成完成：")
    for f in files:
        print(f)
    print("=" * 70)


if __name__ == "__main__":
    main()