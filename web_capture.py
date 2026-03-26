# -*- coding: utf-8 -*-
"""
web_capture.py

【网页截图模块】

作用：
1. 读取主链写入的 capture_path
2. 抓取网页截图（Playwright）
3. 输出标准文件：
   - page_full.png
   - page_viewport.png
   - page_portrait_4x5.png
   - title.txt
   - meta.json

注意：
- 不再写 capture_path
"""

import sys
from pathlib import Path
from PIL import Image
import json
from playwright.sync_api import sync_playwright

BASE_DIR = Path(__file__).resolve().parent
CURRENT_CAPTURE_PATH_FILE = BASE_DIR / "current_capture_path.txt"


def get_capture_path():
    if not CURRENT_CAPTURE_PATH_FILE.exists():
        raise RuntimeError("❌ 找不到 current_capture_path.txt，请先运行主链")

    path = CURRENT_CAPTURE_PATH_FILE.read_text().strip()
    print(f"📌 使用锁定 capture_path：{path}")
    return Path(path)


def make_portrait(src, out):
    img = Image.open(src)
    img = img.resize((1080, 1350))
    img.save(out)


def main():
    if len(sys.argv) < 2:
        raise RuntimeError("❌ 请从主链调用，不要单独运行")

    url = sys.argv[1]
    capture_path = get_capture_path()

    full = capture_path / "page_full.png"
    viewport = capture_path / "page_viewport.png"
    portrait = capture_path / "page_portrait_4x5.png"

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 1600})

        page.goto(url)
        page.wait_for_timeout(3000)

        title = page.title()

        page.screenshot(path=str(full), full_page=True)
        page.screenshot(path=str(viewport))

        browser.close()

    make_portrait(viewport, portrait)

    (capture_path / "title.txt").write_text(title, encoding="utf-8")

    with open(capture_path / "meta.json", "w", encoding="utf-8") as f:
        json.dump({"url": url, "title": title}, f, ensure_ascii=False, indent=2)

    print("✅ web_capture 完成")


if __name__ == "__main__":
    main()