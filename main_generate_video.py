# -*- coding: utf-8 -*-
"""
main_generate_video.py

一键生成视频入口（稳定版）

流程：
1. 输入 topic
2. 输入 angle（可选）
3. 直接调用 script_generator.generate_script()
4. 直接调用 run_pipeline.main()
5. 输出最终视频

设计原则：
- 不使用 subprocess 模拟输入
- 避免 Windows 中文编码问题
- 不改已有主链
"""

import os
import sys

from script_generator import generate_script
import run_pipeline


BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def clean_text(text):
    if text is None:
        return ""
    # 去掉可能的非法 surrogate，避免后续 JSON / HTTP 编码报错
    text = str(text).replace("\r", " ").replace("\n", " ").strip()
    text = text.encode("utf-8", errors="ignore").decode("utf-8", errors="ignore")
    return text


def step_generate_script(topic, angle):
    print("\n=== Step 1: 生成脚本 ===")

    result = generate_script(topic, angle)

    print("\nscript.json 已生成")
    print(f"title : {result.get('title', '')}")

    print("\n预览 cards：")
    for i, card in enumerate(result.get("cards", []), start=1):
        print(f"{i}. [{card.get('type')}] {card.get('text')}")

    return result


def step_run_pipeline():
    print("\n=== Step 2: 生成视频 ===")
    run_pipeline.main()


def main():
    print("\n==============================")
    print(" AI 自动视频生成系统（主入口）")
    print("==============================\n")

    topic = clean_text(input("请输入 topic："))
    angle = clean_text(input("请输入 angle（可选）："))

    if not topic:
        print("❌ topic 不能为空")
        sys.exit(1)

    if not angle:
        angle = None

    try:
        step_generate_script(topic, angle)
        step_run_pipeline()

        print("\n🎉 完成！视频已生成：")
        print("output/video.mp4\n")

    except Exception as e:
        print("\n❌ 主入口运行失败")
        print(e)
        sys.exit(1)


if __name__ == "__main__":
    main()