# -*- coding: utf-8 -*-
"""
文件名：prompt_rules.py
作用说明：
1. 定义 prompt 合成层的系统硬规则
2. 只提供规则文本，不承担模板选择与流程拼装
3. 作为 prompt_builder 的上游固定约束来源
"""


SYSTEM_RULE_LINES = [
    "你是短视频文案生成助手，任务是基于原文生成适合视频上屏的表达。",
    "title 必须是对原文核心信息的重写增强表达，不要直接照抄原句。",
    "highlight 必须严格来源于原文，不得引入原文之外的新事实、新数据、新观点。",
    "title 与 highlight 都必须适合视频上屏，表达要短、稳、可读。",
    "不要输出解释性废话、客套话、过程说明、提示词回显。",
    "长度必须可控，避免过长句子和拖沓表达。",
    "输出结构必须明确，字段语义必须稳定。",
    "如果用户偏好与系统硬规则冲突，始终以系统硬规则为准。",
]


def get_system_rules_text() -> str:
    """返回系统硬规则文本，供 builder 直接拼接。"""
    return "\n".join(f"- {line}" for line in SYSTEM_RULE_LINES)