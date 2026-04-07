# -*- coding: utf-8 -*-
"""
文件名：prompt_templates.py
作用说明：
1. 定义 prompt 合成层使用的内容模板与风格模板
2. 只负责按 mode 返回模板文本，不承担流程控制
3. 对未知 mode 提供稳定 fallback，避免复杂异常
"""


DEFAULT_CONTENT_MODE = "finance"
DEFAULT_STYLE_MODE = "knowledge"


CONTENT_TEMPLATES = {
    "finance": "\n".join(
        [
            "内容类型：finance",
            "聚焦变量关系、因果链条、市场逻辑与决策影响。",
            "优先抓取原文中的价格、利率、风险、收益、预期、变化方向。",
            "title 倾向：把复杂金融信息压缩成一个明确判断。",
            "highlight 倾向：优先提炼关键变量、转折关系、结果判断。",
        ]
    ),
    "product": "\n".join(
        [
            "内容类型：product",
            "聚焦产品对象、使用场景、核心卖点、解决的问题与直接收益。",
            "优先抓取原文中的功能点、差异点、效率提升、体验改善。",
            "title 倾向：突出核心卖点或结果收益。",
            "highlight 倾向：优先提炼功能短语、体验结果、对比优势。",
        ]
    ),
    "ads": "\n".join(
        [
            "内容类型：ads",
            "聚焦传播记忆点、行动驱动、产品价值与受众触发点。",
            "优先抓取原文中的利益点、痛点、转化信号与强记忆表达。",
            "title 倾向：更强调吸引力与记忆点。",
            "highlight 倾向：更强调短促、有冲击力、可重复上屏。",
        ]
    ),
}


STYLE_TEMPLATES = {
    "knowledge": "\n".join(
        [
            "风格类型：knowledge",
            "口气：冷静、解释型、清楚直接。",
            "用词：以概念词、关系词、判断词为主，避免夸张营销词。",
            "信息密度：中高，强调信息清晰度。",
            "highlight 数量倾向：2 到 3 条，覆盖核心概念与关键判断。",
            "title 风格倾向：像一个高信息密度的结论句。",
        ]
    ),
    "authority": "\n".join(
        [
            "风格类型：authority",
            "口气：坚定、专业、判断明确。",
            "用词：偏结论化、偏决策化，减少犹豫表达。",
            "信息密度：高，优先保留最关键的判断。",
            "highlight 数量倾向：2 条左右，强调核心结论和关键依据。",
            "title 风格倾向：更像权威判断或结论压缩。",
        ]
    ),
    "product": "\n".join(
        [
            "风格类型：product",
            "口气：清楚、利落、结果导向。",
            "用词：偏功能收益、效率提升、体验变化。",
            "信息密度：中等，突出卖点，不堆细节。",
            "highlight 数量倾向：2 到 3 条，优先卖点与收益。",
            "title 风格倾向：像一句产品核心价值总结。",
        ]
    ),
    "ads": "\n".join(
        [
            "风格类型：ads",
            "口气：强记忆、强吸引、短促直接。",
            "用词：允许更强的传播感，但不能脱离原文。",
            "信息密度：中等偏低，优先记忆点和转化感。",
            "highlight 数量倾向：3 条左右，优先短、狠、能上屏。",
            "title 风格倾向：更像一条吸睛钩子。",
        ]
    ),
    "story": "\n".join(
        [
            "风格类型：story",
            "口气：有叙事感、有推进感，但不要冗长。",
            "用词：偏转折、变化、冲突、结果。",
            "信息密度：中等，强调信息推进节奏。",
            "highlight 数量倾向：2 到 3 条，优先冲突点和结果点。",
            "title 风格倾向：更像一个带悬念或转折的短句。",
        ]
    ),
}


def _normalize_mode(value: str | None) -> str:
    if value is None:
        return ""
    return str(value).strip().lower()


def get_content_template(content_mode: str) -> str:
    """按 content_mode 返回模板文本，未知值走安全默认。"""
    normalized = _normalize_mode(content_mode)
    return CONTENT_TEMPLATES.get(normalized, CONTENT_TEMPLATES[DEFAULT_CONTENT_MODE])


def get_style_template(style_mode: str) -> str:
    """按 style_mode 返回模板文本，未知值走安全默认。"""
    normalized = _normalize_mode(style_mode)
    return STYLE_TEMPLATES.get(normalized, STYLE_TEMPLATES[DEFAULT_STYLE_MODE])