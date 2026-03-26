# voiceover_engine_v4.py
# -*- coding: utf-8 -*-

import json
import os
import shutil
from typing import Dict, List

SCRIPT_FILE = "script.json"
BACKUP_FILE = "script.voiceover_v4_backup.json"


def load_script(path: str) -> Dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"未找到文件：{path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_script(path: str, data: Dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def backup_script(src: str, dst: str) -> None:
    if os.path.exists(src):
        shutil.copyfile(src, dst)


def validate_script(data: Dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("script.json 顶层必须是对象")

    cards = data.get("cards")
    if not isinstance(cards, list):
        raise ValueError("script.json 中 cards 必须是数组")

    if len(cards) != 5:
        raise ValueError(f"当前系统冻结规则要求 cards 必须固定为 5 张，实际为：{len(cards)}")


def build_hook_voiceover() -> str:
    return (
        "很多人以为，\n"
        "自己在选。\n\n"
        "但其实，\n"
        "是在接风险。"
    )


def build_concept_voiceover() -> str:
    return (
        "真正拉开差距的，\n"
        "不是快。\n\n"
        "是更早，\n"
        "看见风险。"
    )


def build_analogy_voiceover() -> str:
    return (
        "就像过河。\n\n"
        "不是冲。\n"
        "是先站稳。"
    )


def build_example_voiceover() -> str:
    return (
        "工作，投资，关系。\n\n"
        "先看代价的人，\n"
        "通常更稳。"
    )


def build_insight_voiceover() -> str:
    return (
        "所以成熟，\n"
        "不是敢冲。\n\n"
        "是知道，\n"
        "什么不能乱付。"
    )


def build_default_voiceover(text: str) -> str:
    text = str(text).strip().replace("\n", "")
    return f"说白了，\n{text}。"


def build_voiceover(card_type: str, text: str) -> str:
    card_type = str(card_type).strip()

    if card_type == "hook":
        return build_hook_voiceover()
    if card_type == "concept":
        return build_concept_voiceover()
    if card_type == "analogy":
        return build_analogy_voiceover()
    if card_type == "example":
        return build_example_voiceover()
    if card_type == "insight":
        return build_insight_voiceover()

    return build_default_voiceover(text)


def add_voiceover_to_cards(cards: List[Dict]) -> List[Dict]:
    new_cards = []
    for card in cards:
        new_card = dict(card)
        card_type = new_card.get("type", "")
        text = new_card.get("text", "")
        new_card["voiceover"] = build_voiceover(card_type, text)
        new_cards.append(new_card)
    return new_cards


def main():
    print("=== Voiceover Engine V4 开始执行 ===")

    data = load_script(SCRIPT_FILE)
    validate_script(data)

    backup_script(SCRIPT_FILE, BACKUP_FILE)
    print(f"已备份原 script.json -> {BACKUP_FILE}")

    data["cards"] = add_voiceover_to_cards(data["cards"])
    save_script(SCRIPT_FILE, data)

    print(f"已更新 {SCRIPT_FILE}，写入更短、更快的 voiceover")

    print("\n=== 预览结果 ===")
    for i, card in enumerate(data["cards"]):
        print(f"\n[Card {i}] type = {card.get('type', '')}")
        print(f"text      : {card.get('text', '')}")
        print(f"voiceover : {card.get('voiceover', '')}")

    print("\n=== 完成 ===")


if __name__ == "__main__":
    main()