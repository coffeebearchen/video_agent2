# voiceover_engine_v8.py
# -*- coding: utf-8 -*-

"""
voiceover_engine_v8.py

目标：
1. 为 script.json 中每张卡生成更适合短视频真人口播的 voiceover
2. 保持与当前主链兼容
3. 不改动图卡 text，只新增/覆盖 voiceover 字段
4. 优先解决：
   - AI解释腔
   - 句子太长
   - 停顿不自然
   - 口播不够像真人

使用方式：
python voiceover_engine_v8.py

依赖：
pip install openai

环境变量：
OPENAI_API_KEY=你的key
"""

import os
import re
import json
from typing import Dict, List, Any
from openai import OpenAI


SCRIPT_FILE = "script.json"
MODEL_NAME = "gpt-4.1-mini"  # 这里用于生成文案，不是TTS模型


SYSTEM_PROMPT = """
你是一个“中文短视频真人口播文案优化器”。

你的任务不是写文章，也不是写PPT讲稿。
你的任务是把图卡上的一句核心文字，改写成“适合真人短视频口播”的一句短讲解。

你必须严格遵守下面规则：

【核心目标】
生成的文案必须：
- 像真人在镜头前讲
- 短
- 快
- 自然
- 有轻微停顿感
- 不要AI解释腔
- 不要书面腔
- 不要播音腔

【长度规则】
- 每张卡最终口播建议控制在 3~5 句
- 每句尽量短，单句尽量不超过 12 个汉字
- 总长度尽量控制在 28~42 个汉字之间
- 宁可短，不要长
- 宁可留白，不要讲满

【表达规则】
- 要像短视频口播，不像文章
- 可以有轻微转折感
- 可以有轻微“边想边说”的感觉
- 可以有轻微轻松感
- 但不要刻意塞“嗯、啊、那个”
- 除非非常自然，否则不要使用语气词

【禁止事项】
禁止出现：
- “这张图”
- “这张图卡”
- “这一页”
- “前面提到”
- “接下来我们说”
- “首先/其次/最后”
- “换句话说”
- “这意味着”
- “由此可见”
- 任何PPT讲解腔
- 任何文章总结腔
- 任何过度完整、过度工整的句子

【停顿策略】
允许适度使用：
- 逗号
- 句号
- 破折号（——）

但不要堆太多标点。
停顿要像真人口播，而不是朗诵。

【输出要求】
只输出最终口播文案本身。
不要解释。
不要加引号。
不要加序号。
不要输出多版本。
"""


USER_PROMPT_TEMPLATE = """
请根据下面这张卡片的信息，生成一段“中文短视频真人口播文案”。

【卡片类型】
{card_type}

【卡片文字】
{text}

【高亮词】
{highlight}

【额外要求】
1. 必须直接推进观点，不要解释画面
2. 要有一点自然停顿感
3. 要像真人在讲，不像AI在解释
4. 不要太满，允许留白
5. 不要写得太完整，避免书面腔
6. 不要超过 5 句
7. 文案必须适合 TTS 朗读
8. 不要故意模仿夸张主播
9. 不要生硬加入“嗯啊那个”
10. 最终目标是：更快、更自然、更像真人短视频口播

请直接输出最终文案。
"""


def load_script(script_file: str = SCRIPT_FILE) -> Dict[str, Any]:
    with open(script_file, "r", encoding="utf-8") as f:
        return json.load(f)


def save_script(data: Dict[str, Any], script_file: str = SCRIPT_FILE) -> None:
    with open(script_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_text(text: str) -> str:
    """基础清洗：去掉多余空白"""
    if not text:
        return ""
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()


def split_long_sentence(text: str, max_len: int = 12) -> str:
    """
    对过长句子进行保守断开。
    注意：这里只做兜底，不追求完美，避免把模型生成的句子拉得太长。
    """
    if not text:
        return text

    # 先按已有标点切
    parts = re.split(r"(。|，|！|？|——)", text)
    merged = []
    current = ""

    for p in parts:
        if not p:
            continue
        candidate = current + p
        if len(candidate) <= max_len:
            current = candidate
        else:
            if current:
                merged.append(current.strip())
            current = p.strip()

    if current:
        merged.append(current.strip())

    # 再次处理：如果还有特别长的段，按语义弱切分
    final_parts = []
    for part in merged:
        part = part.strip()
        if len(part) <= max_len:
            final_parts.append(part)
            continue

        weak_breaks = ["但是", "不过", "所以", "因为", "如果", "其实", "很多人", "有时候", "问题是", "关键是"]
        cut_done = False
        for wb in weak_breaks:
            idx = part.find(wb, 1)
            if 0 < idx < len(part) - 1:
                a = part[:idx].strip("，。 ")
                b = part[idx:].strip("，。 ")
                if a:
                    final_parts.append(a)
                if b:
                    final_parts.append(b)
                cut_done = True
                break

        if not cut_done:
            # 实在太长，粗略截断
            final_parts.append(part[:max_len].strip("，。 "))
            rest = part[max_len:].strip("，。 ")
            if rest:
                final_parts.append(rest)

    # 清理空项
    final_parts = [x for x in final_parts if x]

    # 重组：尽量形成自然短句
    rebuilt = []
    for i, seg in enumerate(final_parts):
        seg = seg.strip("，。 ")
        if not seg:
            continue

        # 最后一段收句号，前面尽量少用句号
        if i == len(final_parts) - 1:
            rebuilt.append(seg + "。")
        else:
            # 较短句优先用逗号或破折号留出自然停顿
            if len(seg) <= 6 and i == 0:
                rebuilt.append(seg + "——")
            else:
                rebuilt.append(seg + "，")

    return "".join(rebuilt).replace("，，", "，").replace("。。", "。")


def clean_voiceover_text(text: str) -> str:
    """
    对模型返回做二次修整，尽量让它更适合 TTS：
    - 清掉引号
    - 清掉序号
    - 避免多余换行
    - 控制标点密度
    """
    if not text:
        return ""

    text = normalize_text(text)

    # 去掉常见序号
    text = re.sub(r"^\s*[0-9一二三四五六七八九十]+[\.、]\s*", "", text)
    text = re.sub(r"^[\"“”'‘’]+|[\"“”'‘’]+$", "", text)

    # 去掉明显讲解腔
    banned_patterns = [
        r"首先[，,]?",
        r"其次[，,]?",
        r"最后[，,]?",
        r"换句话说[，,]?",
        r"这意味着[，,]?",
        r"由此可见[，,]?",
        r"这张图卡?",
        r"这一页",
        r"前面提到",
        r"接下来我们说",
    ]
    for bp in banned_patterns:
        text = re.sub(bp, "", text)

    # 多个换行压成一个空格，避免TTS读得怪
    text = text.replace("\n", "")

    # 标点轻清洗
    text = re.sub(r"[。]{2,}", "。", text)
    text = re.sub(r"[，]{2,}", "，", text)
    text = re.sub(r"[—]{3,}", "——", text)

    # 如果整体太长，做保守断句
    if len(text) > 42:
        text = split_long_sentence(text, max_len=12)

    return text.strip()


def ensure_human_style(text: str) -> str:
    """
    再做一层兜底：
    - 如果完全没有停顿标记，适当补一点
    - 避免整段像文章
    """
    if not text:
        return text

    # 完全无标点时，尝试补一点
    if not re.search(r"[，。！？——]", text):
        if len(text) > 10:
            text = text[:6] + "——" + text[6:]
        if not text.endswith(("。", "！", "？")):
            text += "。"

    # 如果全是句号，适度换成逗号/破折号
    sentences = [s.strip() for s in re.split(r"[。]", text) if s.strip()]
    if len(sentences) >= 3:
        rebuilt = []
        for i, s in enumerate(sentences):
            if i == 0 and len(s) <= 8:
                rebuilt.append(s + "——")
            elif i == len(sentences) - 1:
                rebuilt.append(s + "。")
            else:
                rebuilt.append(s + "，")
        text = "".join(rebuilt)

    return text.strip()


def build_user_prompt(card: Dict[str, Any]) -> str:
    return USER_PROMPT_TEMPLATE.format(
        card_type=card.get("type", ""),
        text=card.get("text", ""),
        highlight=", ".join(card.get("highlight", [])) if card.get("highlight") else "无"
    )


def generate_voiceover_for_card(client: OpenAI, card: Dict[str, Any]) -> str:
    prompt = build_user_prompt(card)

    response = client.responses.create(
        model=MODEL_NAME,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.8,
    )

    text = response.output_text.strip()
    text = clean_voiceover_text(text)
    text = ensure_human_style(text)

    return text


def update_voiceovers(script_data: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("未检测到 OPENAI_API_KEY 环境变量。")

    client = OpenAI(api_key=api_key)

    cards: List[Dict[str, Any]] = script_data.get("cards", [])
    if not cards:
        raise ValueError("script.json 中没有 cards。")

    for idx, card in enumerate(cards):
        voiceover = generate_voiceover_for_card(client, card)
        card["voiceover"] = voiceover
        print(f"[OK] card_{idx} voiceover: {voiceover}")

    return script_data


def main() -> None:
    script_data = load_script(SCRIPT_FILE)
    script_data = update_voiceovers(script_data)
    save_script(script_data, SCRIPT_FILE)
    print(f"\n已完成 voiceover 生成并写回：{SCRIPT_FILE}")


if __name__ == "__main__":
    main()