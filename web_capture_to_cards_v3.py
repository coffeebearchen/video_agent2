# -*- coding: utf-8 -*-
"""
web_capture_to_cards_v3.py

目标：
1. 读取最新网页截图 page_portrait_4x5.png
2. 先做“去边框/去页面壳”清洗
3. 再按阅读结构裁成 5 张
4. 每张统一输出为 1080x1350

说明：
- 不替换 V2
- 这是 V3 测试版
- 重点解决：
  1) 左右留白 / 顶部壳 / 页面灰底
  2) 图片大小不协调
"""

import os
from PIL import Image

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CAPTURE_DIR = os.path.join(BASE_DIR, "assets", "web_capture")
OUTPUT_DIR = os.path.join(BASE_DIR, "images", "flat")

TARGET_W = 1080
TARGET_H = 1350


def find_latest_capture():
    if not os.path.exists(CAPTURE_DIR):
        raise FileNotFoundError("未找到 web_capture 目录")

    folders = [
        os.path.join(CAPTURE_DIR, d)
        for d in os.listdir(CAPTURE_DIR)
        if os.path.isdir(os.path.join(CAPTURE_DIR, d))
    ]
    if not folders:
        raise ValueError("web_capture 目录为空")

    return sorted(folders)[-1]


def load_main_image(capture_path):
    img_path = os.path.join(capture_path, "page_portrait_4x5.png")
    if not os.path.exists(img_path):
        raise FileNotFoundError(f"未找到截图：{img_path}")
    return Image.open(img_path).convert("RGB")


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def fit_to_canvas(img, target_w=TARGET_W, target_h=TARGET_H):
    """
    把任意图片统一放到固定竖版画布 1080x1350
    保持比例，不拉伸
    """
    src_w, src_h = img.size
    src_ratio = src_w / src_h
    target_ratio = target_w / target_h

    if src_ratio > target_ratio:
        # 太宽，裁左右
        new_w = int(src_h * target_ratio)
        left = (src_w - new_w) // 2
        img = img.crop((left, 0, left + new_w, src_h))
    else:
        # 太高，裁上下
        new_h = int(src_w / target_ratio)
        top = (src_h - new_h) // 2
        img = img.crop((0, top, src_w, top + new_h))

    return img.resize((target_w, target_h), Image.LANCZOS)


def clean_page_shell(img):
    """
    去掉网页外壳、左右留白、顶部壳感
    这是经验值版本，先追求稳定
    """
    w, h = img.size

    left = int(w * 0.08)
    right = int(w * 0.92)
    top = int(h * 0.04)
    bottom = int(h * 0.96)

    cleaned = img.crop((left, top, right, bottom))
    return cleaned


def get_regions(img):
    """
    按阅读结构分成 5 个区域
    """
    w, h = img.size
    return [
        (0, int(0.00 * h), w, int(0.16 * h)),  # 标题区
        (0, int(0.08 * h), w, int(0.32 * h)),  # 标题 + 首图
        (0, int(0.25 * h), w, int(0.52 * h)),  # 正文前段
        (0, int(0.48 * h), w, int(0.76 * h)),  # 正文中段
        (0, int(0.72 * h), w, int(1.00 * h)),  # 结尾区
    ]


def save_cards(img, regions):
    ensure_output_dir()
    files = []

    for i, box in enumerate(regions):
        crop = img.crop(box)
        final_img = fit_to_canvas(crop, TARGET_W, TARGET_H)

        out_path = os.path.join(OUTPUT_DIR, f"card_{i}.png")
        final_img.save(out_path, quality=95)

        print(f"✅ 已生成：{out_path} | size={final_img.size}")
        files.append(out_path)

    return files


def main():
    print("=" * 70)
    print("V3 精准截图模式启动（去边框 + 统一尺寸）")
    print("=" * 70)

    capture_path = find_latest_capture()
    print(f"使用截图目录：{capture_path}")

    raw_img = load_main_image(capture_path)
    print(f"原图尺寸：{raw_img.size}")

    cleaned_img = clean_page_shell(raw_img)
    print(f"清洗后尺寸：{cleaned_img.size}")

    regions = get_regions(cleaned_img)
    print("裁切区域：")
    for i, r in enumerate(regions):
        print(f"Card {i}: {r}")

    files = save_cards(cleaned_img, regions)

    print("=" * 70)
    print("生成完成：")
    for f in files:
        print(f)
    print("=" * 70)


if __name__ == "__main__":
    main()