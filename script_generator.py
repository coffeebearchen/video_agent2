# -*- coding: utf-8 -*-
"""
script_generator.py（支持 topic + angle）
"""

import json
import os
from datetime import datetime

from thinking_engine import generate_thinking

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "output")

SCRIPT_JSON_PATH = os.path.join(BASE_DIR, "script.json")
SCRIPT_DEBUG_PATH = os.path.join(OUTPUT_DIR, "script_debug.txt")


def ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def clean_text(text):
    if not text:
        return ""
    return str(text).replace("\r", " ").replace("\n", " ").strip()


def normalize_cards(cards):
    normalized = []
    for i, card in enumerate(cards, start=1):
        normalized.append({
            "type": clean_text(card.get("type", "concept")),
            "text": clean_text(card.get("text", "")),
            "_card_index": i
        })
    return normalized


def generate_script(topic: str, angle: str = None):
    ensure_output_dir()

    thinking = generate_thinking(topic, angle=angle, save_debug=False)

    script_data = {
        "title": topic,
        "cards": normalize_cards(thinking.get("cards", [])),
        "_meta": {
            "topic": topic,
            "angle": angle,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    }

    with open(SCRIPT_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(script_data, f, ensure_ascii=False, indent=2)

    return script_data


if __name__ == "__main__":
    print("=== script_generator v3（支持 angle）===")

    topic = input("请输入 topic：").strip()
    angle = input("请输入 angle（可选）：").strip()
    angle = angle if angle else None

    result = generate_script(topic, angle)

    print("\nscript.json 已生成")
    print(f"title : {result.get('title', '')}")

    print("\n预览 cards：")
    for i, card in enumerate(result.get("cards", []), start=1):
        print(f"{i}. [{card.get('type')}] {card.get('text')}")

    print("\n完成")