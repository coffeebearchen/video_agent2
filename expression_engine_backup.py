import json
import os
from datetime import datetime


ENGINE_VERSION = "PythonEngine_v0.3"
SCHEMA_VERSION = "1.2"


def split_input_to_topic(raw_text: str) -> str:
    text = (raw_text or "").strip()
    if not text:
        return "为什么很多人总是做错投资决策"

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
    输出五张卡，每张卡都分成：
    - title
    - subtitle
    - body
    - voiceover
    """

    cards = []

    # 1. hook
    cards.append({
        "type": "hook",
        "title": f"{topic_text}",
        "subtitle": "为什么总在关键时候影响结果？",
        "body": "很多人以为自己输在判断太慢，实际上更常见的问题，是一开始就看错了问题的结构。",
        "voiceover": f"{topic_text}，为什么总在关键时候影响结果？很多人以为自己输在判断太慢，实际上更常见的问题，是一开始就看错了问题的结构。"
    })

    # 2. concept
    cards.append({
        "type": "concept",
        "title": "它不是一个孤立问题",
        "subtitle": "表面现象背后，往往有更深层结构",
        "body": "人们看到的是价格、波动和结果，但真正起作用的，往往是隐藏在背后的关系、节奏和判断方式。",
        "voiceover": "它不是一个孤立问题。表面现象背后，往往有更深层结构。人们看到的是价格、波动和结果，但真正起作用的，往往是隐藏在背后的关系、节奏和判断方式。"
    })

    # 3. analogy
    cards.append({
        "type": "analogy",
        "title": "像一根看不见的杠杆",
        "subtitle": "支点对了，小动作也会改变全局",
        "body": "如果支点对了，轻微调整也可能产生巨大变化；如果支点错了，再努力，也可能只是把错误放大。",
        "voiceover": "它像一根看不见的杠杆。支点对了，小动作也会改变全局。如果支点对了，轻微调整也可能产生巨大变化；如果支点错了，再努力，也可能只是把错误放大。"
    })

    # 4. example
    cards.append({
        "type": "example",
        "title": "很多错误，并不是当场发生",
        "subtitle": "而是更早之前就已经埋下了路径",
        "body": "很多人做决定时，只盯着眼前最明显的一点，却忽略了更长的时间结构，于是看似解决问题，实际上是在推迟代价。",
        "voiceover": "很多错误，并不是当场发生，而是更早之前就已经埋下了路径。很多人做决定时，只盯着眼前最明显的一点，却忽略了更长的时间结构，于是看似解决问题，实际上是在推迟代价。"
    })

    # 5. insight
    cards.append({
        "type": "insight",
        "title": "真正重要的，不是答案",
        "subtitle": "而是你看问题的结构方式",
        "body": "一个结果，很少只由最后那一下决定。真正塑造结果的，往往是更早之前的结构、节奏和判断。",
        "voiceover": "真正重要的，不是答案，而是你看问题的结构方式。一个结果，很少只由最后那一下决定。真正塑造结果的，往往是更早之前的结构、节奏和判断。"
    })

    return cards


def build_card(card_id: int, raw_card: dict):
    card_type = raw_card["type"]
    title = raw_card["title"]
    subtitle = raw_card["subtitle"]
    body = raw_card["body"]
    voiceover = raw_card["voiceover"]

    # 保留 text 字段，兼容旧逻辑
    text = f"{title}。{subtitle}。{body}"

    animation = "zoom_in"
    if card_type in ("concept", "insight"):
        animation = "fade_in"

    duration_hint = 4
    if card_type in ("concept", "example"):
        duration_hint = 5

    return {
        "card_id": card_id,
        "type": card_type,

        "title": title,
        "subtitle": subtitle,
        "body": body,

        "text": text,
        "voiceover": voiceover,

        "keywords": [],
        "image_prompt": f"{title} {subtitle} {body}",
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
            "language": "zh"
        },
        "cards": cards,
        "music": {
            "style": "light",
            "volume": 0.3
        },
        "video": {
            "ratio": "9:16",
            "width": 1080,
            "height": 1920,
            "fps": 24
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