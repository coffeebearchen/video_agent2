# -*- coding: utf-8 -*-
"""
core/expression_detector.py

【作用】
最小表达识别器（Task1）

当前职责】
输入一句中文/英文文本，输出：
- expression_type: question | conclusion | transition | emphasis | concept
- carrier: voice | visual | hybrid
- core_text
- confidence
- reasons

【明确边界】
本模块只做表达识别，不做：
- orchestrator
- asset_selector
- build_scene_assets
- audio_mixer
- video_engine
- UI
- 大模型调用

【设计原则】
1. 先可运行
2. 规则清晰
3. 输出稳定
4. 便于后续被 orchestrator 接入
"""

from __future__ import annotations

import re
from typing import List

from models.schema import ExpressionInput, ExpressionResult


class ExpressionDetector:
    """
    最小可运行表达识别器

    当前采用“规则优先”的安全实现：
    - 低复杂度
    - 可解释
    - 可控
    - 不漂移
    """

    QUESTION_KEYWORDS = {
        "为什么", "什么", "怎么", "是否", "到底", "何时", "如何"
    }

    CONCLUSION_KEYWORDS = {
        "因此", "所以", "这意味着", "说明", "可以看到", "结论是"
    }

    TRANSITION_KEYWORDS = {
        "但是", "不过", "然而", "可是"
    }

    EMPHASIS_KEYWORDS = {
        "真正", "核心", "关键", "本质", "一定要", "最重要"
    }

    CONCEPT_KEYWORDS = {
        "为什么", "什么是", "原理", "逻辑", "概念", "结构", "模型", "系统", "趋势",
        "周期", "风险", "利率", "债券", "股票", "比特币", "国债", "经济", "金融",
        "方法", "框架", "策略", "知识", "认知", "规律", "机制", "解释",
        "concept", "logic", "model", "system", "theory", "framework", "risk", "finance"
    }

    VISUAL_KEYWORDS = {
        "画面", "镜头", "感觉", "氛围", "情绪", "美感", "冲击", "视觉", "无声",
        "音乐", "bgm", "节奏感", "让人感受到", "表达感", "场景", "演出", "图像",
        "image", "visual", "scene", "mood", "music", "cinematic"
    }

    VOICE_KEYWORDS = {
        "讲", "说", "解释", "旁白", "字幕", "表达", "口播", "文案", "听", "语音",
        "voice", "narration", "speech", "talk", "explain"
    }

    def detect(self, text: str) -> ExpressionResult:
        """
        对输入文本进行最小表达识别

        参数：
            text: 用户输入的一句话

        返回：
            ExpressionResult
        """
        cleaned_text = self._normalize_text(text)
        self._validate_text(cleaned_text)

        visual_score, visual_reasons = self._score_keywords(
            cleaned_text, self.VISUAL_KEYWORDS, "命中视觉载体关键词"
        )
        voice_score, voice_reasons = self._score_keywords(
            cleaned_text, self.VOICE_KEYWORDS, "命中声音载体关键词"
        )

        expression_type, expression_reasons = self._decide_expression_type(cleaned_text)

        carrier, carrier_reasons = self._decide_carrier(
            visual_score=visual_score,
            voice_score=voice_score
        )

        reasons: List[str] = []
        reasons.extend(visual_reasons)
        reasons.extend(voice_reasons)
        reasons.extend(expression_reasons)
        reasons.extend(carrier_reasons)

        confidence = self._calculate_confidence(
            expression_type=expression_type,
            expression_reasons=expression_reasons,
            visual_score=visual_score,
            voice_score=voice_score
        )

        core_text = cleaned_text

        return ExpressionResult(
            expression_type=expression_type,
            carrier=carrier,
            core_text=core_text,
            confidence=confidence,
            reasons=reasons
        )

    def detect_from_input(self, data: ExpressionInput) -> ExpressionResult:
        """
        为后续统一主链保留的输入接口
        """
        return self.detect(data.raw_text)

    @staticmethod
    def _normalize_text(text: str) -> str:
        """
        统一清洗输入文本
        """
        if text is None:
            return ""

        text = text.strip()
        text = re.sub(r"\s+", " ", text)
        return text

    @staticmethod
    def _validate_text(text: str) -> None:
        """
        校验输入文本
        """
        if not text:
            raise ValueError("输入不能为空。请至少输入一句话。")

        if len(text) < 2:
            raise ValueError("输入过短。请至少输入两个字符以上。")

    @staticmethod
    def _score_keywords(text: str, keywords: set, reason_prefix: str):
        """
        关键词打分
        """
        score = 0
        reasons: List[str] = []

        for kw in keywords:
            if kw.lower() in text.lower():
                score += 1
                reasons.append(f"{reason_prefix}：{kw}")

        return score, reasons

    def _decide_expression_type(self, text: str):
        """
        决定表达类型
        """
        if "？" in text or "?" in text:
            reasons = ["命中问句特征：？" if "？" in text else "命中问句特征：?"]
            for keyword in self._find_matched_keywords(text, self.QUESTION_KEYWORDS):
                reasons.append(f"命中问句关键词：{keyword}")
            reasons.append("按优先级判定为 question")
            return "question", reasons

        question_keywords = self._find_matched_keywords(text, self.QUESTION_KEYWORDS)
        if question_keywords:
            reasons = [f"命中问句关键词：{keyword}" for keyword in question_keywords]
            reasons.append("按优先级判定为 question")
            return "question", reasons

        conclusion_keywords = self._find_matched_keywords(text, self.CONCLUSION_KEYWORDS)
        if conclusion_keywords:
            reasons = [f"命中结论关键词：{keyword}" for keyword in conclusion_keywords]
            reasons.append("按优先级判定为 conclusion")
            return "conclusion", reasons

        transition_keywords = self._find_matched_keywords(text, self.TRANSITION_KEYWORDS)
        if transition_keywords:
            reasons = [f"命中转折关键词：{keyword}" for keyword in transition_keywords]
            reasons.append("按优先级判定为 transition")
            return "transition", reasons

        emphasis_keywords = self._find_matched_keywords(text, self.EMPHASIS_KEYWORDS)
        if emphasis_keywords:
            reasons = [f"命中强调关键词：{keyword}" for keyword in emphasis_keywords]
            reasons.append("按优先级判定为 emphasis")
            return "emphasis", reasons

        concept_keywords = self._find_matched_keywords(text, self.CONCEPT_KEYWORDS)
        if concept_keywords:
            reasons = [f"命中概念关键词：{keyword}" for keyword in concept_keywords]
            reasons.append("未命中更高优先级类型，判定为 concept")
            return "concept", reasons

        return "concept", ["未命中特征词，按保底规则判定为 concept"]

    @staticmethod
    def _find_matched_keywords(text: str, keywords: set) -> List[str]:
        """
        返回命中的关键词列表
        """
        lowered_text = text.lower()
        matched_keywords: List[str] = []

        for keyword in keywords:
            if keyword.lower() in lowered_text:
                matched_keywords.append(keyword)

        return matched_keywords

    @staticmethod
    def _decide_carrier(visual_score: int, voice_score: int):
        """
        决定表达载体
        """
        reasons: List[str] = []

        if visual_score > 0 and voice_score > 0:
            reasons.append("同时存在视觉与声音表达特征，判定为 hybrid")
            return "hybrid", reasons

        if visual_score > 0:
            reasons.append("视觉表达特征更明显，判定为 visual")
            return "visual", reasons

        if voice_score > 0:
            reasons.append("声音表达特征更明显，判定为 voice")
            return "voice", reasons

        reasons.append("未命中载体关键词，按安全默认值判定为 voice")
        return "voice", reasons

    @staticmethod
    def _calculate_confidence(
        expression_type: str,
        expression_reasons: List[str],
        visual_score: int,
        voice_score: int
    ) -> float:
        """
        置信度计算
        这里只做最小可解释规则，不引入复杂算法。
        """
        if expression_type == "question":
            return 0.9

        if expression_type == "conclusion":
            return 0.82

        if expression_type == "transition":
            return 0.78

        if expression_type == "emphasis":
            return 0.72

        total = len(expression_reasons) + visual_score + voice_score

        if total <= 0:
            return 0.55
        if total == 1:
            return 0.65
        if total == 2:
            return 0.75
        if total == 3:
            return 0.85

        return 0.92


def detect_expression(text: str) -> ExpressionResult:
    """
    便捷函数接口
    """
    detector = ExpressionDetector()
    return detector.detect(text)


if __name__ == "__main__":
    demo_text = "为什么利率变化会影响普通人的生活？"
    result = detect_expression(demo_text)
    print(result.to_dict())