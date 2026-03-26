# -*- coding: utf-8 -*-
# tts_engine_compare.py

import os
import json
from typing import Dict, List

from openai import OpenAI
from mutagen.mp3 import MP3

SCRIPT_FILE = "script.json"
AUDIO_COMPARE_DIR = "audio_compare"

MODEL_NAME = "gpt-4o-mini-tts"
VOICE_LIST = ["alloy", "marin", "cedar"]
SPEED = 1.35

INSTRUCTIONS = (
    "请用中文短视频口播风格朗读。"
    "语速偏快，但必须清楚。"
    "像真人在说话，不要播音腔。"
    "有一点自然起伏，可以有很轻的口语感。"
    "停顿要短，不要拖。"
    "语气自然，直接，有一点点人味。"
)


def load_script(path: str) -> Dict:
    if not os.path.exists(path):
        raise FileNotFoundError(f"未找到文件：{path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def ensure_dir(path: str) -> None:
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


def normalize_text(text: str) -> str:
    if not text:
        return ""
    return str(text).strip()


def get_audio_path(voice_name: str, index: int) -> str:
    voice_dir = os.path.join(AUDIO_COMPARE_DIR, voice_name)
    ensure_dir(voice_dir)
    return os.path.join(voice_dir, f"audio_{index}.mp3")


def get_mp3_duration_seconds(path: str) -> float:
    audio = MP3(path)
    return round(float(audio.info.length), 2)


def generate_one_tts(client: OpenAI, voice_name: str, text: str, output_path: str) -> None:
    with client.audio.speech.with_streaming_response.create(
        model=MODEL_NAME,
        voice=voice_name,
        input=text,
        instructions=INSTRUCTIONS,
        speed=SPEED,
        response_format="mp3",
    ) as response:
        response.stream_to_file(output_path)


def main():
    print("=== OpenAI TTS Compare 开始执行 ===")

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

    ensure_dir(AUDIO_COMPARE_DIR)

    cards: List[Dict] = data["cards"]

    summary = {}

    for voice_name in VOICE_LIST:
        print(f"\n==============================")
        print(f"开始生成 voice = {voice_name}")
        print(f"==============================")

        summary[voice_name] = []

        for i, card in enumerate(cards):
            voiceover = normalize_text(card.get("voiceover", ""))
            if not voiceover:
                raise ValueError(f"第 {i} 张卡缺少 voiceover，无法生成语音")

            output_path = get_audio_path(voice_name, i)

            print(f"\n[生成语音] voice={voice_name} card={i}")
            print(f"voiceover : {voiceover}")
            print(f"输出文件  : {output_path}")

            generate_one_tts(client, voice_name, voiceover, output_path)

            if not os.path.exists(output_path):
                raise FileNotFoundError(f"语音生成失败，未找到文件：{output_path}")

            duration = get_mp3_duration_seconds(output_path)
            summary[voice_name].append(duration)

            print(f"duration  : {duration} 秒")

    print("\n=== 三音色时长汇总 ===")
    for voice_name, durations in summary.items():
        total = round(sum(durations), 2)
        print(f"\nvoice = {voice_name}")
        print(f"durations = {durations}")
        print(f"total     = {total} 秒")

    print("\n=== 完成 ===")
    print("请到下面目录试听：")
    for voice_name in VOICE_LIST:
        print(os.path.join(AUDIO_COMPARE_DIR, voice_name))


if __name__ == "__main__":
    main()