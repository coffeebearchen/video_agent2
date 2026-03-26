import json
import os
from datetime import datetime


ENGINE_VERSION = "PythonEngine_v0.3_ultra_fast_test"
SCHEMA_VERSION = "1.2"


def split_input_to_topic(raw_text: str) -> str:
    text = (raw_text or "").strip()
    if not text:
        return "为什么很多人越努力，结果反而越差"

    text = text.replace("\r\n", "\n").replace("\r", "\n").strip()

    first_line = ""
    for line in text.split("\n"):
        line = line.strip()
        if line:
            first_line = line
            break

    if not first_line:
        first_line = text

    return first_line[:80]


def build_card_content(topic_text: str):
    """
    极速测试版：
    只输出 3 张卡，加快整条链测试速度
    """

    cards = []

    # 1. hook
    cards.append({
        "type": "hook",
        "title": f"{topic_text}",
        "subtitle": "很多问题，不是努力不够，而是方向错了",
        "body": "人们常常以为结果差，是因为投入不够，但更常见的情况，是一开始就站错了位置。",
        "voiceover": f"{topic_text}。很多问题，并不是努力不够，而是方向错了。人们常常以为结果差，是因为投入不够，但更常见的情况，是一开始就站错了位置。"
    })

    # 2. analogy
    cards.append({
        "type": "analogy",
        "title": "像在错误的地图上拼命赶路",
        "subtitle": "走得越快，不一定离目标越近",
        "body": "如果地图本身就错了，那么加快速度，只会更快到达错误的地方。",
        "voiceover": "它就像在一张错误的地图上拼命赶路。走得越快，不一定离目标越近。如果地图本身就错了，那么加快速度，只会更快到达错误的地方。"
    })

    # 3. insight
    cards.append({
        "type": "insight",
        "title": "真正重要的，是先确认结构",
        "subtitle": "先看清，再行动",
        "body": "很多结果，并不是由最后一次努力决定，而是由更早之前的判断结构决定。",
        "voiceover": "真正重要的，是先确认结构，再决定是否投入。很多结果，并不是由最后一次努力决定，而是由更早之前的判断结构决定。"
    })

    return cards


def build_card(card_id: int, raw_card: dict):
    card_type = raw_card["type"]
    title = raw_card["title"]
    subtitle = raw_card["subtitle"]
    body = raw_card["body"]
    voiceover = raw_card["voiceover"]

    text = f"{title}。{subtitle}。{body}"

    animation = "fade_in"
    if card_type == "hook":
        animation = "zoom_in"

    # 极速测试版：更短
    duration_hint = 1
    if card_type == "analogy":
        duration_hint = 2

    return {
        "card_id": card_id,
        "type": card_type,

        "title": title,
        "subtitle": subtitle,
        "body": body,

        "text": text,
        "voiceover": voiceover,

        "keywords": [],
        "image_prompt": f"{title} {subtitle}",
        "tags": [card_type],
        "clip_hint": "",
        "duration_hint": duration_hint,

        "visual": {
            "layout": "image_overlay_bottom",
            "animation": animation
        }
    }


def build_script(raw_text: str):
    topic_text = split_input_to_topic(raw_text)
    raw_cards = build_card_content(topic_text)

    cards = []
    for idx, raw_card in enumerate(raw_cards, start=1):
        cards.append(build_card(idx, raw_card))

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    script = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": now_str,
        "engine_version": ENGINE_VERSION,
        "meta": {
            "topic": topic_text,
            "author_style": "default",
            "depth_level": 1,
            "language": "zh",
            "test_mode": "ultra_fast"
        },
        "cards": cards,
        "music": {
            "style": "light",
            "volume": 0.0
        },
        "video": {
            "ratio": "9:16",
            "width": 360,
            "height": 640,
            "fps": 6
        }
    }

    return script


def save_script(script: dict, output_path: str = "output/script.json"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)


def generate_script(raw_text: str, output_path: str = "output/script.json"):
    script = build_script(raw_text)
    save_script(script, output_path)
    return script