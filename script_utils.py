import json
import os


REQUIRED_TOP_LEVEL_KEYS = [
    "schema_version",
    "meta",
    "cards",
    "music",
    "video"
]

REQUIRED_CARD_KEYS = [
    "card_id",
    "type",
    "text",
    "voiceover",
    "image_prompt",
    "tags",
    "clip_hint",
    "duration_hint"
]


def load_script(script_path: str = "output/script.json") -> dict:
    if not os.path.exists(script_path):
        raise FileNotFoundError(f"找不到 script 文件: {script_path}")

    with open(script_path, "r", encoding="utf-8") as f:
        return json.load(f)


def normalize_card_fields(card: dict) -> dict:
    """
    给卡片补齐新旧兼容字段：
    - title
    - subtitle
    - body
    - text
    """

    title = str(card.get("title", "") or "").strip()
    subtitle = str(card.get("subtitle", "") or "").strip()
    body = str(card.get("body", "") or "").strip()
    text = str(card.get("text", "") or "").strip()

    # 如果没有 title/subtitle/body，但有 text，就做简单兼容
    if not title and text:
        title = text

    if "title" not in card:
        card["title"] = title

    if "subtitle" not in card:
        card["subtitle"] = subtitle

    if "body" not in card:
        card["body"] = body

    if not text:
        merged = " ".join([x for x in [title, subtitle, body] if x]).strip()
        card["text"] = merged
    else:
        card["text"] = text

    return card


def validate_script(script: dict):
    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in script:
            raise ValueError(f"script.json 缺少顶层字段: {key}")

    if not isinstance(script["cards"], list) or not script["cards"]:
        raise ValueError("script.json 的 cards 必须是非空列表")

    for i, card in enumerate(script["cards"], start=1):
        for key in REQUIRED_CARD_KEYS:
            if key not in card:
                raise ValueError(f"第 {i} 张卡片缺少字段: {key}")

        card = normalize_card_fields(card)

        if "visual" not in card:
            card["visual"] = {
                "layout": "image_overlay_bottom",
                "animation": "zoom_in"
            }

        if "duration_hint" not in card or not isinstance(card["duration_hint"], int):
            card["duration_hint"] = 4

        script["cards"][i - 1] = card

    if "fps" not in script["video"]:
        script["video"]["fps"] = 24

    return script


def save_debug_text(script: dict, output_path: str = "output/script_debug.txt"):
    lines = []
    lines.append("=== SCRIPT DEBUG VIEW ===")
    lines.append(f"schema_version: {script.get('schema_version', '')}")
    lines.append(f"generated_at: {script.get('generated_at', '')}")
    lines.append(f"engine_version: {script.get('engine_version', '')}")
    lines.append(f"topic: {script.get('meta', {}).get('topic', '')}")
    lines.append("")

    for card in script.get("cards", []):
        lines.append(f"[Card {card.get('card_id')}] {card.get('type')}")
        lines.append(f"title: {card.get('title', '')}")
        lines.append(f"subtitle: {card.get('subtitle', '')}")
        lines.append(f"body: {card.get('body', '')}")
        lines.append(f"text: {card.get('text', '')}")
        lines.append(f"voiceover: {card.get('voiceover', '')}")
        lines.append(f"image_prompt: {card.get('image_prompt', '')}")
        lines.append(f"animation: {card.get('visual', {}).get('animation', '')}")
        lines.append(f"duration_hint: {card.get('duration_hint', '')}")
        lines.append("-" * 50)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))