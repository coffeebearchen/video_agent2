# -*- coding: utf-8 -*-
"""
web_capture_mobile.py

作用：
1. 输入一个网页 URL（优先从 input_url.txt 读取）
2. 使用“移动端浏览器模式”打开网页
3. 保存整页截图 / 视口截图
4. 自动生成适合短视频的 4:5 图片
5. 保存网页标题和 meta 信息

说明：
- 这是单独测试版
- 不替换 web_capture.py
- 不接入主链
- 先只测试“移动端网页截图效果”
"""

import re
import json
from datetime import datetime
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright


# =========================
# 基础配置
# =========================
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_ROOT = BASE_DIR / "assets" / "web_capture_mobile"
INPUT_URL_FILE = BASE_DIR / "input_url.txt"

# iPhone 12 近似视口
MOBILE_WIDTH = 390
MOBILE_HEIGHT = 844

# 4:5 竖版短视频图
PORTRAIT_WIDTH = 1080
PORTRAIT_HEIGHT = 1350

WAIT_MS = 4500


def safe_name(text: str, max_len: int = 60) -> str:
    text = text.strip()
    text = re.sub(r"[\\/:*?\"<>|]", "_", text)
    text = re.sub(r"\s+", "_", text)
    if len(text) > max_len:
        text = text[:max_len]
    return text or "untitled"


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def center_crop_to_ratio(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    src_w, src_h = img.size
    target_ratio = target_w / target_h
    src_ratio = src_w / src_h

    if src_ratio > target_ratio:
        new_w = int(src_h * target_ratio)
        left = (src_w - new_w) // 2
        box = (left, 0, left + new_w, src_h)
    else:
        new_h = int(src_w / target_ratio)
        top = (src_h - new_h) // 2
        box = (0, top, src_w, top + new_h)

    cropped = img.crop(box)
    resized = cropped.resize((target_w, target_h), Image.LANCZOS)
    return resized


def make_portrait_image(src_path: Path, out_path: Path):
    img = Image.open(src_path).convert("RGB")
    portrait = center_crop_to_ratio(img, PORTRAIT_WIDTH, PORTRAIT_HEIGHT)
    portrait.save(out_path, quality=95)


def load_url() -> str:
    if INPUT_URL_FILE.exists():
        url = INPUT_URL_FILE.read_text(encoding="utf-8").strip()
        if url:
            print(f"检测到 input_url.txt，自动使用 URL：{url}")
            return url

    print("请输入网页 URL：")
    return input().strip()


def try_hide_common_popups(page):
    """
    尝试隐藏常见浮层/固定条，不保证所有网站都有效
    """
    js = """
    (() => {
      const selectors = [
        '[class*="popup"]',
        '[class*="modal"]',
        '[class*="dialog"]',
        '[class*="cookie"]',
        '[class*="consent"]',
        '[class*="banner"]',
        '[class*="ad"]',
        '[id*="popup"]',
        '[id*="modal"]',
        '[id*="dialog"]',
        '[id*="cookie"]',
        '[id*="consent"]',
        '[id*="banner"]',
        '[id*="ad"]'
      ];

      selectors.forEach(sel => {
        document.querySelectorAll(sel).forEach(el => {
          const style = window.getComputedStyle(el);
          const isFixed = style.position === 'fixed' || style.position === 'sticky';
          const bigEnough = el.offsetWidth > 100 || el.offsetHeight > 50;
          if (isFixed || bigEnough) {
            el.style.display = 'none';
            el.style.visibility = 'hidden';
            el.style.opacity = '0';
          }
        });
      });

      // 尝试隐藏顶部固定栏
      document.querySelectorAll('*').forEach(el => {
        const style = window.getComputedStyle(el);
        if ((style.position === 'fixed' || style.position === 'sticky') && el.offsetHeight < 180) {
          el.style.display = 'none';
        }
      });
    })();
    """
    try:
        page.evaluate(js)
    except Exception:
        pass


def capture_website_mobile(url: str):
    now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = safe_name(url.replace("https://", "").replace("http://", ""))
    out_dir = OUTPUT_ROOT / f"{now_str}_{folder_name}"
    ensure_dir(out_dir)

    full_path = out_dir / "page_full.png"
    viewport_path = out_dir / "page_viewport.png"
    portrait_path = out_dir / "page_portrait_4x5.png"
    title_path = out_dir / "title.txt"
    meta_path = out_dir / "meta.json"

    print("=" * 70)
    print("开始移动端网页截图...")
    print(f"URL: {url}")
    print(f"输出目录: {out_dir}")
    print("=" * 70)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        iphone_12 = p.devices["iPhone 12"]
        context = browser.new_context(**iphone_12, locale="zh-CN")
        page = context.new_page()

        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(WAIT_MS)

        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass

        try_hide_common_popups(page)
        page.wait_for_timeout(1000)

        title = page.title().strip()

        # 整页截图
        page.screenshot(path=str(full_path), full_page=True)

        # 当前视口截图
        page.screenshot(path=str(viewport_path), full_page=False)

        context.close()
        browser.close()

    # 生成 4:5 图
    make_portrait_image(viewport_path, portrait_path)

    with open(title_path, "w", encoding="utf-8") as f:
        f.write(title if title else "")

    meta = {
        "url": url,
        "title": title,
        "created_at": now_str,
        "mode": "mobile",
        "full_screenshot": str(full_path),
        "viewport_screenshot": str(viewport_path),
        "portrait_4x5": str(portrait_path),
        "mobile_width": MOBILE_WIDTH,
        "mobile_height": MOBILE_HEIGHT,
        "portrait_width": PORTRAIT_WIDTH,
        "portrait_height": PORTRAIT_HEIGHT
    }

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print("✅ 移动端截图完成")
    print(f"标题: {title}")
    print(f"整页截图: {full_path}")
    print(f"视口截图: {viewport_path}")
    print(f"4:5竖版图: {portrait_path}")
    print(f"Meta: {meta_path}")
    print("=" * 70)


def main():
    ensure_dir(OUTPUT_ROOT)

    url = load_url()
    if not url:
        raise ValueError("URL 不能为空")

    if not url.startswith("http://") and not url.startswith("https://"):
        print("检测到你没有输入协议头，已自动补上 https://")
        url = "https://" + url

    try:
        capture_website_mobile(url)
    except Exception as e:
        print(f"❌ 移动端截图失败：{e}")


if __name__ == "__main__":
    main()