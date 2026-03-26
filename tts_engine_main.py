# -*- coding: utf-8 -*-
"""
tts_engine_main.py

主链专用 TTS 模块（兼容 scene_plan 升级版）
- 使用 edge-tts 生成语音
- 优先读取：data/current/scene_plan.json
- 再读取：scene_plan.json
- 最后回退：script.json
- 输出：audio/card_0.mp3 ~ card_4.mp3

特点：
1. 优先支持 scene 中间层
2. 没有 scene 时自动回退到旧 script.json
3. 每个 mp3 生成后立即检查是否存在
4. 打印每条文本，方便确认是否是新脚本
"""

import os
import json
import asyncio
import edge_tts


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "audio")

SCENE_PATH_NEW = os.path.join(BASE_DIR, "data", "current", "scene_plan.json")
SCENE_PATH_OLD = os.path.join(BASE_DIR, "scene_plan.json")
SCRIPT_PATH = os.path.join(BASE_DIR, "script.json")

DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"
DEFAULT_RATE = "+0%"
DEFAULT_VOLUME = "+0%"


def ensure_audio_dir():
    os.makedirs(AUDIO_DIR, exist_ok=True)


def clean_text(text):
    if not text:
        return ""
    return str(text).replace("\r", " ").replace("\n", " ").strip()


def load_cards_from_scene(scene_path):
    with open(scene_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    scenes = data.get("scenes", [])
    if not isinstance(scenes, list) or not scenes:
        raise ValueError(f"{scene_path} 中没有有效的 scenes")

    cards = []
    for i, scene in enumerate(scenes):
        text = clean_text(scene.get("text", ""))
        if not text:
            continue

        cards.append({
            "type": "scene",
            "text": text,
            "scene_id": scene.get("scene_id", i + 1),
            "duration": scene.get("duration", None)
        })

    if not cards:
        raise ValueError(f"{scene_path} 中 scenes 为空或 text 无效")

    return cards, scene_path


def load_cards_from_script():
    if not os.path.exists(SCRIPT_PATH):
        raise FileNotFoundError(f"未找到 script.json：{SCRIPT_PATH}")

    with open(SCRIPT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    cards = data.get("cards", [])
    if not isinstance(cards, list) or not cards:
        raise ValueError("script.json 中没有有效的 cards")

    return cards, SCRIPT_PATH


def load_cards():
    """
    读取优先级：
    1. data/current/scene_plan.json
    2. 根目录 scene_plan.json
    3. 根目录 script.json
    """
    if os.path.exists(SCENE_PATH_NEW):
        return load_cards_from_scene(SCENE_PATH_NEW)

    if os.path.exists(SCENE_PATH_OLD):
        return load_cards_from_scene(SCENE_PATH_OLD)

    return load_cards_from_script()


async def _generate_one_tts_async(text: str, output_file: str):
    communicate = edge_tts.Communicate(
        text=text,
        voice=DEFAULT_VOICE,
        rate=DEFAULT_RATE,
        volume=DEFAULT_VOLUME,
    )
    await communicate.save(output_file)


def generate_tts(text: str, index: int) -> str:
    ensure_audio_dir()

    text = clean_text(text)
    if not text:
        raise ValueError(f"第 {index} 条 TTS 文本为空")

    output_file = os.path.join(AUDIO_DIR, f"card_{index}.mp3")

    print("-" * 70)
    print(f"[TTS] Card {index}")
    print(f"文本：{text}")
    print(f"输出：{output_file}")

    asyncio.run(_generate_one_tts_async(text, output_file))

    if not os.path.exists(output_file):
        raise FileNotFoundError(f"TTS 生成后未找到文件：{output_file}")

    file_size = os.path.getsize(output_file)
    if file_size <= 0:
        raise ValueError(f"TTS 文件为空：{output_file}")

    print(f"✅ 已生成：{output_file} ({file_size} bytes)")
    return output_file


def clear_old_audio():
    ensure_audio_dir()
    removed = 0
    for name in os.listdir(AUDIO_DIR):
        if name.lower().endswith(".mp3"):
            file_path = os.path.join(AUDIO_DIR, name)
            try:
                os.remove(file_path)
                removed += 1
            except Exception as e:
                print(f"⚠️ 删除旧音频失败：{file_path} | {e}")
    print(f"🧹 已清理旧音频数量：{removed}")


def generate_all_tts(cards):
    ensure_audio_dir()
    clear_old_audio()

    audio_files = []

    for i, card in enumerate(cards):
        text = clean_text(card.get("text", ""))
        audio_file = generate_tts(text, i)
        audio_files.append(audio_file)

    return audio_files


def main():
    print("=" * 70)
    print("开始生成 TTS...")
    print(f"优先 Scene 文件：{SCENE_PATH_NEW}")
    print(f"回退 Scene 文件：{SCENE_PATH_OLD}")
    print(f"最终回退 Script 文件：{SCRIPT_PATH}")
    print(f"音频目录：{AUDIO_DIR}")
    print("=" * 70)

    cards, source_path = load_cards()

    print(f"当前使用内容来源：{source_path}")
    print(f"读取到条目数量：{len(cards)}")

    for i, card in enumerate(cards):
        print(f"Card {i} | type={card.get('type', '')} | text={clean_text(card.get('text', ''))}")

    files = generate_all_tts(cards)

    print("=" * 70)
    print("TTS 生成完成：")
    for f in files:
        print(f)
    print("=" * 70)


if __name__ == "__main__":
    main()