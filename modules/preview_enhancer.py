# -*- coding: utf-8 -*-
"""
文件名：preview_enhancer.py
作用说明：
1. 将 title + highlight 映射成更像视频脚本的极简结构
2. 强化展示层的“可直接拿去做视频”的感知
3. 不负责模型调用与业务判断
"""


def build_enhanced_preview(title: str, highlight: list[str]) -> dict:
    """将标题与重点映射为 headline + scenes 结构。"""
    title_text = str(title or "").strip()
    highlight_items = [str(item or "").strip() for item in highlight if str(item or "").strip()]

    scenes = []
    if title_text:
        scenes.append({"text": title_text})

    for item in highlight_items:
        scenes.append({"text": item})

    if not scenes:
        scenes.append({"text": "内容待生成"})

    return {
        "headline": title_text or scenes[0]["text"],
        "scenes": scenes,
    }