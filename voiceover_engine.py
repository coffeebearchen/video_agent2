# -*- coding: utf-8 -*-
"""
voiceover_engine.py

作用：
1. 读取 script.json
2. 给每张卡自动重建 voiceover 字段
3. 保持原有 text / highlight / type 结构不变
4. 输出更像短视频口播的讲解文案

当前版本目标：
- 禁止出现“这张画面 / 这张图卡 / 这一页 / 前面一页 / 前面一部分”等表达
- 改成短视频口播腔
- 更直接
- 更像真人顺着内容往下讲
- 句子更短，更利于后续 TTS 自然停顿
"""

import json
import os
import shutil
from typing import Dict, List


SCRIPT_FILE = "script.json"
BACKUP_FILE = "script.voiceover_backup.json"


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


def normalize_text(text: str) -> str:
    if not text:
        return ""
    return str(text).strip().replace("\n", "")


def clean_for_voice(text: str) -> str:
    return normalize_text(text)


def build_hook_voiceover(text: str) -> str:
    t = clean_for_voice(text)
    return (
        f"很多人平时觉得自己是在做选择。"
        f"但其实，更真实的情况是，{t}。"
        f"问题往往不在选哪一个，而在你有没有看清背后的代价。"
    )


def build_concept_voiceover(text: str) -> str:
    t = clean_for_voice(text)
    return (
        f"真正拉开差距的，往往不是谁更快，谁更敢冲。"
        f"更重要的是，{t}。"
        f"你越早看清风险，后面走得就越稳。"
    )


def build_analogy_voiceover(text: str) -> str:
    t = clean_for_voice(text)
    return (
        f"这个道理说白了，就像过河。"
        f"不是跳得越快越厉害。"
        f"反而是每一步站得住，更重要。"
        f"所以很多时候，{t}。"
    )


def build_example_voiceover(text: str) -> str:
    t = clean_for_voice(text)
    return (
        f"放到现实里，这种差别其实特别常见。"
        f"不管是工作、投资，还是关系选择，{t}。"
        f"看不清代价的人，往往走着走着就会失控。"
    )


def build_insight_voiceover(text: str) -> str:
    t = clean_for_voice(text)
    return (
        f"所以最后你会发现，成熟从来不是更敢冲。"
        f"更重要的是，{t}。"
        f"真正厉害的人，通常都知道什么该抓，什么代价不能乱付。"
    )


def build_default_voiceover(text: str) -> str:
    t = clean_for_voice(text)
    return (
        f"换个更直接的说法，{t}。"
        f"很多问题一旦从这个角度看，就会清楚很多。"
    )


def build_voiceover(card_type: str, text: str) -> str:
    t = normalize_text(text)
    if not t:
        return ""

    if card_type == "hook":
        return build_hook_voiceover(t)
    if card_type == "concept":
        return build_concept_voiceover(t)
    if card_type == "analogy":
        return build_analogy_voiceover(t)
    if card_type == "example":
        return build_example_voiceover(t)
    if card_type == "insight":
        return build_insight_voiceover(t)

    return build_default_voiceover(t)


def add_voiceover_to_cards(cards: List[Dict], overwrite_existing: bool = True) -> List[Dict]:
    new_cards = []

    for card in cards:
        card_type = str(card.get("type", "")).strip()
        text = normalize_text(card.get("text", ""))

        new_card = dict(card)

        existing_voiceover = str(new_card.get("voiceover", "")).strip()
        if existing_voiceover and not overwrite_existing:
            new_cards.append(new_card)
            continue

        new_card["voiceover"] = build_voiceover(card_type, text)
        new_cards.append(new_card)

    return new_cards


def validate_script(data: Dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("script.json 顶层必须是对象")

    cards = data.get("cards")
    if not isinstance(cards, list):
        raise ValueError("script.json 中 cards 必须是数组")

    if len(cards) != 5:
        raise ValueError(f"当前系统冻结规则要求 cards 必须固定为 5 张，实际为：{len(cards)}")


def main():
    print("=== Voiceover Engine 开始执行 ===")

    data = load_script(SCRIPT_FILE)
    validate_script(data)

    backup_script(SCRIPT_FILE, BACKUP_FILE)
    print(f"已备份原 script.json -> {BACKUP_FILE}")

    data["cards"] = add_voiceover_to_cards(data["cards"], overwrite_existing=True)

    save_script(SCRIPT_FILE, data)
    print(f"已更新 {SCRIPT_FILE}，为每张卡重建 voiceover 字段")

    print("\n=== 预览结果 ===")
    for i, card in enumerate(data["cards"]):
        print(f"\n[Card {i}] type = {card.get('type', '')}")
        print(f"text      : {card.get('text', '')}")
        print(f"voiceover : {card.get('voiceover', '')}")

    print("\n=== 完成 ===")


if __name__ == "__main__":
    main()