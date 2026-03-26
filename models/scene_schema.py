# -*- coding: utf-8 -*-
"""
models/scene_schema.py

【作用】
定义 Task2 使用的最小场景数据结构。

【当前阶段】
仅服务于：
1. core/orchestrator.py
2. runner/task2_runner.py

【边界】
- 只定义 Task2 需要的数据结构
- 不修改 Task1 的 schema.py
- 不引入第三方依赖
"""

from __future__ import annotations

from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any


@dataclass
class SceneItem:
    """
    单个场景项

    scene_type:
        - hook: 引子/问题抛出
        - main: 主表达
        - highlight: 强调/收束
    """
    scene_id: int
    scene_type: str
    text: str
    duration: float
    source: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ScenePlan:
    """
    场景计划
    """
    input_text: str
    expression_type: str
    carrier: str
    scenes: List[SceneItem] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Task2Output:
    """
    Task2 Runner 的统一输出结构
    """
    success: bool
    input_text: str
    expression_type: str
    carrier: str
    scene_plan: ScenePlan
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)