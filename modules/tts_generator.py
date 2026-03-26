import os
from gtts import gTTS


def generate_tts(text: str, output_dir: str, lang: str = "zh-cn") -> str:
    if not text or not text.strip():
        raise ValueError("voiceover 不能为空。")

    voice_path = os.path.join(output_dir, "voice.mp3")
    tts = gTTS(text=text, lang=lang)
    tts.save(voice_path)
    return voice_path