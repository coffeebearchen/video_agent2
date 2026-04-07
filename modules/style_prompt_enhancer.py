# -*- coding: utf-8 -*-
"""
文件名：style_prompt_enhancer.py
作用说明：
1. 在不改 prompt_builder 结构的前提下，强化不同 style_mode 的表达差异
2. 为产品 demo 路径提供更明确的风格约束
3. 只负责 prompt 文本增强，不负责模型调用与结果解析
"""


STYLE_FORCE_RULES = {
    "knowledge": {
        "display_name": "知识型",
        "goal": "像在把一件事讲明白，冷静、解释型、带因果或关系判断。",
        "title_rule": "title 要像认知结论，优先使用 本质上 / 关键在于 / 不是……而是…… 这类结构。",
        "highlight_rule": "highlight 固定输出 2~3 条，至少 1 条体现因果、解释或关系。",
        "must": [
            "必须写出解释型结构，而不是只下判断。",
            "必须出现因果关系、条件关系或不是……而是……的关系表达。",
            "必须保留知识密度，像在解释核心逻辑。",
        ],
        "prefer": [
            "本质上……",
            "关键在于……",
            "因为……所以……",
            "不是……而是……",
        ],
        "forbid": [
            "不要强情绪。",
            "不要营销口号感。",
            "不要像老板在拍板。",
        ],
    },
    "authority": {
        "display_name": "老板型",
        "goal": "像老板或主理人在下结论，短、硬、压缩，少解释。",
        "title_rule": "title 必须是一句判断，优先使用 不要只看…… / 关键是…… / 真正重要的是……。",
        "highlight_rule": "highlight 固定输出 1~2 条，越短越好，不展开原因链。",
        "must": [
            "必须是压缩后的判断，不要讲课。",
            "必须减少补充说明，直接说结论。",
            "必须显得更硬，更像拍板，而不是分析。",
        ],
        "prefer": [
            "不要只看……",
            "关键是……",
            "真正重要的是……",
            "核心不是……而是……",
        ],
        "forbid": [
            "不要长解释。",
            "不要学术化。",
            "不要出现讲课感、铺垫感。",
        ],
    },
    "ads": {
        "display_name": "广告型",
        "goal": "突出记忆点和冲击力。",
        "title_rule": "title 要短促直接。",
        "highlight_rule": "highlight 2~3 条，强调卖点。",
        "must": [
            "表达必须有冲击力。",
            "句子必须短促。",
            "必须有明显记忆点。",
        ],
        "prefer": [
            "直接点结果。",
            "直接点价值。",
        ],
        "forbid": [
            "不要长句。",
            "不要解释性展开。",
            "不要学术化表达。",
        ],
    },
    "story": {
        "display_name": "故事型",
        "goal": "像短视频口播开场，有转折、有代入、有推进。",
        "title_rule": "title 必须有转折感或误区感，优先使用 很多人以为……但其实…… / 别只看…… / 你以为……其实……。",
        "highlight_rule": "highlight 固定输出 2~3 条，至少 1 条必须带转折或误区结构。",
        "must": [
            "必须出现转折、误区或对比结构。",
            "必须带一点情绪推进，但不能脱离原文。",
            "必须像视频开头，而不是说明文。",
        ],
        "prefer": [
            "很多人以为……",
            "但真正……",
            "别只看……",
            "你以为……其实……",
        ],
        "forbid": [
            "不要纯讲解。",
            "不要纯判断。",
            "不要写成冷静说明书。",
        ],
    },
    "product": {
        "display_name": "产品型",
        "goal": "突出卖点和结果收益。",
        "title_rule": "title 要直接点价值。",
        "highlight_rule": "highlight 2~3 条，聚焦卖点。",
        "must": [
            "必须突出结果收益。",
            "必须点出卖点。",
            "表达要利落直接。",
        ],
        "prefer": [
            "直接点结果。",
            "直接点差异。",
        ],
        "forbid": [
            "不要空泛表达。",
            "不要脱离产品场景。",
            "不要写成知识讲解。",
        ],
    },
}


DEFAULT_STYLE_RULES = STYLE_FORCE_RULES["knowledge"]


def _build_rule_section(style_mode: str) -> str:
    rules = STYLE_FORCE_RULES.get(str(style_mode or "").strip().lower(), DEFAULT_STYLE_RULES)
    lines = [
        "[风格强化约束]",
        f"当前目标风格：{rules['display_name']}",
        f"风格目标：{rules['goal']}",
        f"title 要求：{rules['title_rule']}",
        f"highlight 要求：{rules['highlight_rule']}",
        "必须遵守：",
    ]

    for item in rules["must"]:
        lines.append(f"- {item}")

    lines.append("优先采用的句式：")
    for item in rules["prefer"]:
        lines.append(f"- {item}")

    lines.append("禁止出现：")
    for item in rules["forbid"]:
        lines.append(f"- {item}")

    lines.extend(
        [
            "所有内容必须紧贴原文，不得编造原文没有的新事实。",
            "title 和 highlight 必须彼此风格一致，不要只改个别词。",
            "输出必须严格为 JSON。",
            '输出结构固定为：{"title":"...","highlight":["...","..."]}',
            "不要输出 prompt_summary、不要输出解释、不要输出代码块。",
        ]
    )
    return "\n".join(lines)


def enhance_style_prompt(style_mode: str, base_prompt: str) -> str:
    """基于已有 prompt 文本附加强风格约束。"""
    base_text = str(base_prompt or "").strip()
    enhancement = _build_rule_section(style_mode)
    if not base_text:
        return enhancement
    return f"{base_text}\n\n{enhancement}"