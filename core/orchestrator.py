# -*- coding: utf-8 -*-
"""
core/orchestrator.py

【作用】
Task2 最小场景组织器（Orchestrator）

【当前职责】
把 ExpressionResult 转成最小 ScenePlan：
- hook
- main
- highlight

【明确边界】
本模块只做场景组织，不做：
- asset_selector
- build_scene_assets
- audio_mixer
- video_engine
- UI
- 大模型调用

【设计原则】
1. 先可运行
2. 规则明确
3. 输出稳定
4. 与 Task1 接口兼容
"""

from __future__ import annotations

from typing import List

from models.schema import ExpressionResult
from models.scene_schema import SceneItem, ScenePlan


class Orchestrator:
    """
    最小可运行场景组织器
    """

    def build_scene_plan(self, input_text: str, expression_result: ExpressionResult) -> ScenePlan:
        """
        根据表达识别结果，构建最小场景计划
        """
        if not input_text or not input_text.strip():
            raise ValueError("input_text 不能为空。")

        if expression_result is None:
            raise ValueError("expression_result 不能为空。")

        scenes = self._build_scenes(
            input_text=input_text.strip(),
            expression_result=expression_result
        )

        return ScenePlan(
            input_text=input_text.strip(),
            expression_type=expression_result.expression_type,
            carrier=expression_result.carrier,
            scenes=scenes
        )

    def _build_scenes(self, input_text: str, expression_result: ExpressionResult) -> List[SceneItem]:
        """
        构建最小场景列表
        """
        expression_type = expression_result.expression_type
        carrier = expression_result.carrier
        core_text = expression_result.core_text.strip()

        # 根据表达类型决定最小场景模板
        if expression_type == "hero":
            return self._build_hero_scenes(core_text=core_text, carrier=carrier)

        if expression_type == "hybrid":
            return self._build_hybrid_scenes(core_text=core_text, carrier=carrier)

        # 默认按 concept
        return self._build_concept_scenes(core_text=core_text, carrier=carrier)

    @staticmethod
    def _carrier_source_label(carrier: str) -> str:
        """
        输出一个简洁的来源标签，便于后续主链接入。
        """
        if carrier == "visual":
            return "orchestrator:visual"
        if carrier == "hybrid":
            return "orchestrator:hybrid"
        return "orchestrator:voice"

    def _build_concept_scenes(self, core_text: str, carrier: str) -> List[SceneItem]:
        """
        概念型表达 → 3段最小场景
        """
        source = self._carrier_source_label(carrier)

        hook_text = f"先抛出一个问题：{core_text}"
        main_text = f"核心解释对象是：{core_text}"
        highlight_text = "把这个概念讲清楚，比只记结论更重要。"

        return [
            SceneItem(
                scene_id=1,
                scene_type="hook",
                text=hook_text,
                duration=2.0,
                source=source
            ),
            SceneItem(
                scene_id=2,
                scene_type="main",
                text=main_text,
                duration=4.0,
                source=source
            ),
            SceneItem(
                scene_id=3,
                scene_type="highlight",
                text=highlight_text,
                duration=2.0,
                source=source
            )
        ]

    def _build_hero_scenes(self, core_text: str, carrier: str) -> List[SceneItem]:
        """
        人物型表达 → 3段最小场景
        """
        source = self._carrier_source_label(carrier)

        hook_text = f"先看这个人物表达：{core_text}"
        main_text = f"主体真正想传达的是：{core_text}"
        highlight_text = "人物表达的关键，不只是说了什么，而是怎么被感受到。"

        return [
            SceneItem(
                scene_id=1,
                scene_type="hook",
                text=hook_text,
                duration=2.0,
                source=source
            ),
            SceneItem(
                scene_id=2,
                scene_type="main",
                text=main_text,
                duration=4.0,
                source=source
            ),
            SceneItem(
                scene_id=3,
                scene_type="highlight",
                text=highlight_text,
                duration=2.5,
                source=source
            )
        ]

    def _build_hybrid_scenes(self, core_text: str, carrier: str) -> List[SceneItem]:
        """
        混合型表达 → 4段最小场景
        """
        source = self._carrier_source_label(carrier)

        hook_text = f"这个问题既有人物表达，也有概念表达：{core_text}"
        main_text_1 = f"先抓住主体表达：{core_text}"
        main_text_2 = f"再抓住背后的概念结构：{core_text}"
        highlight_text = "真正有表现力的内容，往往是人物与概念同时成立。"

        return [
            SceneItem(
                scene_id=1,
                scene_type="hook",
                text=hook_text,
                duration=2.0,
                source=source
            ),
            SceneItem(
                scene_id=2,
                scene_type="main",
                text=main_text_1,
                duration=3.0,
                source=source
            ),
            SceneItem(
                scene_id=3,
                scene_type="main",
                text=main_text_2,
                duration=3.0,
                source=source
            ),
            SceneItem(
                scene_id=4,
                scene_type="highlight",
                text=highlight_text,
                duration=2.0,
                source=source
            )
        ]


def build_scene_plan(input_text: str, expression_result: ExpressionResult) -> ScenePlan:
    """
    便捷函数接口
    """
    orchestrator = Orchestrator()
    return orchestrator.build_scene_plan(input_text=input_text, expression_result=expression_result)


if __name__ == "__main__":
    from core.expression_detector import detect_expression

    demo_text = "为什么利率变化会影响普通人的生活？"
    demo_result = detect_expression(demo_text)
    demo_scene_plan = build_scene_plan(demo_text, demo_result)

    print(demo_scene_plan.to_dict())