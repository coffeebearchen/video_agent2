import json
import os
from openai import OpenAI
from mutagen.mp3 import MP3

SCRIPT_FILE = "script.json"
AUDIO_DIR = "audio"

MODEL = "gpt-4o-mini-tts"
VOICE = "alloy"

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_duration(file):

    audio = MP3(file)
    return round(audio.info.length, 2)


def generate_tts(text, output_file):

    with client.audio.speech.with_streaming_response.create(
        model=MODEL,
        voice=VOICE,
        input=text
    ) as response:

        response.stream_to_file(output_file)


def main():

    with open(SCRIPT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not os.path.exists(AUDIO_DIR):
        os.makedirs(AUDIO_DIR)

    for i, card in enumerate(data["cards"]):

        text = card["voiceover"]

        audio_file = f"{AUDIO_DIR}/audio_{i}.mp3"

        print(f"\n生成语音 Card {i}")
        print(text)

        generate_tts(text, audio_file)

        duration = get_duration(audio_file)

        card["audio_file"] = audio_file
        card["duration"] = duration

        print("duration:", duration)

    with open(SCRIPT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("\nTTS完成")


if __name__ == "__main__":
    main()