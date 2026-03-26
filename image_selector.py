# -*- coding: utf-8 -*-
"""
image_selector.py
========================================================
作用：
1. 读取 image_library.json
2. 根据 script.json 每张卡的 type + text 自动匹配图片
3. 尽量避免重复选同一张图
"""

import json
import os
from typing import Dict, List, Any


LIBRARY_FILE = "image_library.json"


KEYWORD_TO_TAGS = {
    "努力": ["growth", "direction", "path"],
    "方向": ["direction", "road", "path", "choice"],
    "选择": ["choice", "decision", "balance"],
    "判断": ["judgment", "balance", "choice"],
    "投资": ["investment", "balance", "risk"],
    "风险": ["risk", "collapse", "pressure"],
    "结构": ["structure", "balance", "direction"],
    "时间": ["time", "growth", "future"],
    "成长": ["growth", "future", "patience"],
    "错误": ["mistake", "road", "direction"],
    "问题": ["conflict", "pressure", "structure"],
    "突破": ["growth", "future", "path"],
    "决策": ["decision", "choice", "balance"],
    "道路": ["road", "path", "direction"],
    "路径": ["road", "path", "direction"],
    "平衡": ["balance", "judgment", "choice"],
    "冲突": ["conflict", "pressure", "risk"],
    "压力": ["pressure", "risk", "collapse"],
    "崩塌": ["collapse", "risk", "conflict"],
    "耐心": ["patience", "growth", "time"],
    "未来": ["future", "growth", "time"]
}


DEFAULT_TYPE_TAGS = {
    "hook": ["choice", "risk", "direction"],
    "concept": ["structure", "balance", "growth"],
    "analogy": ["road", "path", "balance"],
    "example": ["decision", "pressure", "risk"],
    "insight": ["growth", "future", "balance"]
}


def load_image_library(library_file: str = LIBRARY_FILE) -> List[Dict[str, Any]]:
    if not os.path.exists(library_file):
        raise FileNotFoundError(f"找不到图库索引文件：{library_file}")

    with open(library_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise RuntimeError("image_library.json 顶层必须是列表。")

    valid_items = []
    for item in data:
        if not isinstance(item, dict):
            continue
        if "file" not in item:
            continue

        item.setdefault("tags", [])
        item.setdefault("type_tags", [])

        # 只保留真实存在的图片
        if os.path.exists(item["file"]):
            valid_items.append(item)

    if not valid_items:
        raise RuntimeError("image_library.json 中没有任何有效图片路径。")

    return valid_items


def extract_tags_from_text(text: str) -> List[str]:
    tags: List[str] = []

    for keyword, mapped_tags in KEYWORD_TO_TAGS.items():
        if keyword in text:
            tags.extend(mapped_tags)

    # 去重但保持顺序
    seen = set()
    result = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            result.append(tag)

    return result


def score_image(item: Dict[str, Any], card_type: str, text_tags: List[str]) -> int:
    score = 0

    item_tags = item.get("tags", [])
    type_tags = item.get("type_tags", [])

    # type 匹配
    if card_type in type_tags:
        score += 6

    # 文本关键词匹配
    for tag in text_tags:
        if tag in item_tags:
            score += 3

    return score


def pick_best_image_for_card(
    card: Dict[str, Any],
    image_library: List[Dict[str, Any]],
    used_files: List[str]
) -> str:
    card_type = card.get("type", "")
    text = card.get("text", "")

    text_tags = extract_tags_from_text(text)
    if not text_tags:
        text_tags = DEFAULT_TYPE_TAGS.get(card_type, ["balance"])

    scored = []
    for item in image_library:
        file_path = item.get("file", "")
        if not file_path:
            continue

        score = score_image(item, card_type, text_tags)

        # 如果已经用过，强力降权
        if file_path in used_files:
            score -= 100

        scored.append((score, file_path))

    if not scored:
        return ""

    scored.sort(key=lambda x: x[0], reverse=True)

    # 优先返回未重复的最佳项
    for score, file_path in scored:
        if file_path not in used_files:
            return file_path

    # 如果真的图不够，才允许重复
    return scored[0][1]


def select_images_for_script(script_data: Dict[str, Any], library_file: str = LIBRARY_FILE) -> List[str]:
    image_library = load_image_library(library_file)
    cards = script_data.get("cards", [])

    selected_images: List[str] = []
    used_files: List[str] = []

    for card in cards:
        selected = pick_best_image_for_card(card, image_library, used_files)
        selected_images.append(selected)

        if selected:
            used_files.append(selected)

    return selected_images