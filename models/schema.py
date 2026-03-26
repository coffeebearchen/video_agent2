# -*- coding: utf-8 -*-
"""
models/schema.py

【作用】
定义 Task1 使用的统一数据结构，避免模块之间接口漂移。

【当前阶段】
仅服务于：
1. core/expression_detector.py
2. runner/mvp_runner.py

【边界】
- 只定义 Task1 需要的数据结构
- 不引入数据库
- 不引入第三方依赖
- 不扩展为全系统 schema
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any


@dataclass
class ExpressionInput:
    """表达检测输入结构"""
    raw_text: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ExpressionResult:
    """
    表达检测输出结构

    expression_type:
        - hero: 人物/主体表达为主
        - concept: 概念/知识表达为主
        - hybrid: 人物 + 概念混合

    carrier:
        - voice: 更适合声音/旁白驱动
        - visual: 更适合画面/情绪驱动
        - hybrid: 声音与画面混合
    """
    expression_type: str
    carrier: str
    core_text: str
    confidence: float
    reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Task1Output:
    """
    Task1 Runner 的统一输出结构
    """
    success: bool
    input_text: str
    result: ExpressionResult
    message: str

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        return data