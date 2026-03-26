# -*- coding: utf-8 -*-
"""
thinking_engine.py（支持 topic + angle）
"""

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com/v1"
)


def generate_thinking(topic, angle=None, save_debug=False):
    angle_text = f"\n视角：{angle}" if angle else ""

    prompt = f"""
请围绕以下主题，生成一个短视频结构内容（5段）：

主题：
{topic}
{angle_text}

要求：
1. 必须严格输出5段（hook / concept / analogy / impact / emotion）
2. 用生活化语言
3. 避免重复句式开头
4. 每段一句话，控制在30字以内
5. 表达要自然，不要AI腔

输出格式：
[
  {{ "type": "hook", "text": "..." }},
  {{ "type": "concept", "text": "..." }},
  {{ "type": "analogy", "text": "..." }},
  {{ "type": "impact", "text": "..." }},
  {{ "type": "emotion", "text": "..." }}
]
"""

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是一个短视频内容创作者"},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    content = response.choices[0].message.content.strip()

    import json
    cards = json.loads(content)

    return {
        "title": topic,
        "cards": cards,
        "topic": topic,
        "angle": angle,
        "engine_version": "deepseek_v1",
        "structure_name": "5段结构",
        "logic_chain": []
    }