# tts_engine_v3.py
# -*- coding: utf-8 -*-

import os
import json
import shutil
from typing import Dict, List

from openai import OpenAI
from mutagen.mp3 import MP3

SCRIPT_FILE = "script.json"
BACKUP_FILE = "script.tts_v3_backup.json"
AUDIO_DIR = "audio"

MODEL_NAME = "gpt-4o-mini-tts"
VOICE_NAME = "alloy"


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


def ensure_audio_dir(path: str) -> None:
    if not os.path.exists(path):
        os.makedirs(path)


def validate_script(data: Dict) -> None:
    if not isinstance(data, dict):
        raise ValueError("script.json 顶层必须是对象")

    cards = data.get("cards")
    if not isinstance(cards, list):
        raise ValueError("script.json 中 cards 必须是数组")

    if len(cards) != 5:
        raise ValueError(f"当前系统冻结规则要求 cards 必须固定为 5 张，实际为：{len(cards)}")


def get_audio_path(index: int) -> str:
    return os.path.join(AUDIO_DIR, f"audio_{index}.mp3")


def get_mp3_duration_seconds(path: str) -> float:
    audio = MP3(path)
    return round(float(audio.info.length), 2)


def normalize_text(text: str) -> str:
    if not text:
        return ""
    return str(text).strip()


def generate_one_tts(client: OpenAI, text: str, output_path: str) -> None:
    # 这里故意不再加长提示词，避免被读出来，也避免整体节奏变慢
    with client.audio.speech.with_streaming_response.create(
        model=MODEL_NAME,
        voice=VOICE_NAME,
        input=text,
        response_format="mp3",
    ) as response:
        response.stream_to_file(output_path)


def generate_all_tts(client: OpenAI, cards: List[Dict]) -> List[Dict]:
    new_cards = []

    for i, card in enumerate(cards):
        new_card = dict(card)

        voiceover = normalize_text(new_card.get("voiceover", ""))
        if not voiceover:
            raise ValueError(f"第 {i} 张卡缺少 voiceover，无法生成语音")

        output_path = get_audio_path(i)

        print(f"\n[生成语音] Card {i}")
        print(f"voiceover : {voiceover}")
        print(f"输出文件  : {output_path}")

        generate_one_tts(client, voiceover, output_path)

        if not os.path.exists(output_path):
            raise FileNotFoundError(f"语音生成失败，未找到文件：{output_path}")

        duration = get_mp3_duration_seconds(output_path)
        new_card["audio_file"] = output_path.replace("\\", "/")
        new_card["duration"] = duration

        print(f"duration  : {duration} 秒")

        new_cards.append(new_card)

    return new_cards


def main():
    print("=== OpenAI TTS Engine V3 开始执行 ===")

    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError(
            "未检测到 OPENAI_API_KEY。请先执行：\n"
            'setx OPENAI_API_KEY "你的APIKey"\n'
            "然后关闭当前命令行窗口，再重新打开后运行。"
        )

    client = OpenAI(api_key=api_key)

    data = load_script(SCRIPT_FILE)
    validate_script(data)

    backup_script(SCRIPT_FILE, BACKUP_FILE)
    print(f"已备份原 script.json -> {BACKUP_FILE}")

    ensure_audio_dir(AUDIO_DIR)
    print(f"已确认音频目录存在 -> {AUDIO_DIR}/")

    data["cards"] = generate_all_tts(client, data["cards"])
    save_script(SCRIPT_FILE, data)

    print(f"\n已更新 {SCRIPT_FILE}，写入 audio_file 和 duration")

    print("\n=== 结果预览 ===")
    for i, card in enumerate(data["cards"]):
        print(f"\n[Card {i}]")
        print(f"text      : {card.get('text', '')}")
        print(f"voiceover : {card.get('voiceover', '')}")
        print(f"audio_file: {card.get('audio_file', '')}")
        print(f"duration  : {card.get('duration', '')}")

    print("\n=== 完成 ===")


if __name__ == "__main__":
    main()