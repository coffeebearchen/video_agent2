# -*- coding: utf-8 -*-
"""
文件名：auto_directives_generator.py
作用说明：
1. 在没有手工 directives 结果时，自动生成最小可用的 visual_inserts
2. 在没有手工 expression_enhancements 时，自动生成最小可用的强调结构
3. 让自动生成结果受 style preset 控制
4. 保持自动生成是默认草稿层，不覆盖手工控制

设计边界：
1. 不做 AI / NLP / 语义理解
2. 只使用固定规则、固定素材、固定位置
3. 只服务于 SCRIPT -> SCENE 阶段
"""

from __future__ import annotations

from modules.script_directives_utils import (
    DEFAULT_SCENE_REFERENCE_DURATION,
    clean_text,
    distribute_insert_timings,
)


DEFAULT_AUTO_INSERT_FILE = "assets/inserts/default.png"
DEFAULT_AUTO_INSERT_SCALE = 0.2
DEFAULT_AUTO_ENHANCEMENT_TYPE = "popup"
DEFAULT_STYLE_PRESET = "serious"
DEFAULT_MAX_AUTO_INSERTS = 2

STYLE_PROFILES = {
    "serious": {
        "insert_count_mode": "always_one",
        "insert_positions_single": ["center"],
        "insert_positions_multi": ["center"],
        "insert_duration": 1.4,
        "insert_scale": 0.2,
        "enhancement_min_text_length": 12,
        "enhancement_text_max_length": 8,
        "enhancement_position": "top",
        "enhancement_start": 0.6,
        "enhancement_end": 1.6,
    },
    "fast": {
        "insert_count_mode": "fast_mode",
        "insert_positions_single": ["center"],
        "insert_positions_multi": ["top", "bottom"],
        "insert_duration": 0.8,
        "insert_scale": 0.2,
        "enhancement_min_text_length": 8,
        "enhancement_text_max_length": 12,
        "enhancement_position": "top",
        "enhancement_start": 0.4,
        "enhancement_end": 1.2,
    },
    "story": {
        "insert_count_mode": "story_mode",
        "insert_positions_single": ["center"],
        "insert_positions_multi": ["center", "bottom"],
        "insert_duration": 1.1,
        "insert_scale": 0.2,
        "enhancement_min_text_length": 10,
        "enhancement_text_max_length": 10,
        "enhancement_position": "center",
        "enhancement_start": 0.5,
        "enhancement_end": 1.5,
    },
}


def normalize_style_preset(style_preset):
    """将输入 preset 收敛为 serious / fast / story。"""
    normalized = clean_text(style_preset).lower() or DEFAULT_STYLE_PRESET
    if normalized not in STYLE_PROFILES:
        return DEFAULT_STYLE_PRESET, True

    return normalized, False


def get_style_profile(style_preset):
    """返回当前 style preset 的最小规则配置。"""
    normalized_preset, _ = normalize_style_preset(style_preset)
    return STYLE_PROFILES[normalized_preset]


def normalize_max_auto_inserts(max_auto_inserts):
    """将 auto insert 上限收敛到 Task30 允许的 1~2。"""
    if isinstance(max_auto_inserts, bool):
        return DEFAULT_MAX_AUTO_INSERTS, True

    normalized_value = None
    if isinstance(max_auto_inserts, int):
        normalized_value = max_auto_inserts
    elif isinstance(max_auto_inserts, str):
        stripped = max_auto_inserts.strip()
        if stripped.isdigit():
            normalized_value = int(stripped)

    if normalized_value not in (1, 2):
        return DEFAULT_MAX_AUTO_INSERTS, True

    return normalized_value, False


def _get_text_length_level(text):
    """按稳定的 UTF-8 字节长度划分文本档位。"""
    cleaned = clean_text(text)
    text_length = len(cleaned.encode("utf-8")) if cleaned else 0
    if text_length <= 0:
        return "empty"
    if text_length <= 36:
        return "short"
    if text_length <= 72:
        return "medium"
    return "long"


def _resolve_insert_count(text, style_preset):
    """根据文本长度档位和 style preset 决定 insert 数量。"""
    text_level = _get_text_length_level(text)
    if text_level == "empty":
        return 0

    profile = get_style_profile(style_preset)
    count_mode = profile["insert_count_mode"]
    if count_mode == "always_one":
        return 1

    if count_mode == "fast_mode":
        if text_level == "short":
            return 1
        return 2

    if count_mode == "story_mode":
        if text_level == "long":
            return 2
        return 1

    return 1


def should_generate_visual_inserts(text, existing_visual_inserts):
    """判断当前 scene 是否应自动生成 visual_inserts。"""
    if isinstance(existing_visual_inserts, list) and existing_visual_inserts:
        return False

    cleaned = clean_text(text)
    return bool(cleaned)


def should_generate_enhancements(text, existing_enhancements):
    """判断当前 scene 是否应自动生成 expression_enhancements。"""
    if isinstance(existing_enhancements, list) and existing_enhancements:
        return False

    cleaned = clean_text(text)
    return bool(cleaned)


def build_auto_visual_insert_candidates(text, style_preset):
    """根据文本长度生成基础 visual_insert 草稿。"""
    cleaned = clean_text(text)
    if not cleaned:
        return []

    profile = get_style_profile(style_preset)
    insert_count = _resolve_insert_count(cleaned, style_preset)
    if insert_count <= 0:
        return []

    if insert_count == 1:
        positions = list(profile["insert_positions_single"])
    else:
        positions = list(profile["insert_positions_multi"])

    candidates = []
    for position in positions[:insert_count]:
        candidates.append(
            {
                "type": "image",
                "file": DEFAULT_AUTO_INSERT_FILE,
                "path": DEFAULT_AUTO_INSERT_FILE,
                "position": position,
                "scale": profile["insert_scale"],
                "duration": profile["insert_duration"],
            }
        )

    return candidates


def build_auto_expression_enhancement(text, style_preset):
    """根据文本生成最多 1 个最小强调结构。"""
    cleaned = clean_text(text)
    profile = get_style_profile(style_preset)
    if len(cleaned) < profile["enhancement_min_text_length"]:
        return []

    enhancement_text = cleaned[: profile["enhancement_text_max_length"]]
    if not enhancement_text:
        return []

    return [
        {
            "type": DEFAULT_AUTO_ENHANCEMENT_TYPE,
            "text": enhancement_text,
            "start": profile["enhancement_start"],
            "end": profile["enhancement_end"],
            "position": profile["enhancement_position"],
        }
    ]


def generate_auto_directives(
    text,
    existing_visual_inserts=None,
    existing_enhancements=None,
    scene_duration=DEFAULT_SCENE_REFERENCE_DURATION,
    style_preset=DEFAULT_STYLE_PRESET,
    auto_enabled=True,
    max_auto_inserts=DEFAULT_MAX_AUTO_INSERTS,
):
    """统一生成 auto directives，并返回结果与日志。"""
    cleaned_text = clean_text(text)
    normalized_style_preset, fallback_used = normalize_style_preset(style_preset)
    normalized_max_auto_inserts, max_fallback_used = normalize_max_auto_inserts(max_auto_inserts)
    logs = ["开始评估是否需要自动生成"]
    if fallback_used:
        logs.append(f"style preset 非法，已回退 {DEFAULT_STYLE_PRESET}")
    if max_fallback_used:
        logs.append(
            f"max_auto_inserts 非法，已回退 {DEFAULT_MAX_AUTO_INSERTS}"
        )
    logs.append(f"使用 style preset：{normalized_style_preset}")
    logs.append(f"max_auto_inserts = {normalized_max_auto_inserts}")

    result = {
        "visual_inserts": [],
        "expression_enhancements": [],
        "logs": logs,
    }

    if not auto_enabled:
        logs.append("auto_directives 已关闭，跳过自动生成")
        return result

    if not cleaned_text:
        logs.append("text 为空，跳过自动生成")
        return result

    if isinstance(existing_visual_inserts, list) and existing_visual_inserts:
        logs.append("已存在手工 visual_inserts，跳过自动生成")
    elif should_generate_visual_inserts(cleaned_text, existing_visual_inserts):
        logs.append(f"使用默认插图素材：{DEFAULT_AUTO_INSERT_FILE}")
        visual_candidates = build_auto_visual_insert_candidates(cleaned_text, normalized_style_preset)
        original_candidate_count = len(visual_candidates)
        if original_candidate_count > normalized_max_auto_inserts:
            visual_candidates = visual_candidates[:normalized_max_auto_inserts]
            logs.append(
                f"max_auto_inserts={normalized_max_auto_inserts}，"
                f"已裁切 auto visual_inserts 为 {len(visual_candidates)} 项"
            )
        result["visual_inserts"] = distribute_insert_timings(
            visual_candidates,
            scene_duration=scene_duration,
            logs=logs,
        )
        logs.append(
            f"基于 style={normalized_style_preset} 自动生成 visual_inserts："
            f"{len(result['visual_inserts'])} 项"
        )
    else:
        logs.append("text 不满足 visual_inserts 自动生成条件，跳过")

    if isinstance(existing_enhancements, list) and existing_enhancements:
        logs.append("已存在手工 expression_enhancements，跳过自动生成")
    elif should_generate_enhancements(cleaned_text, existing_enhancements):
        result["expression_enhancements"] = build_auto_expression_enhancement(
            cleaned_text,
            normalized_style_preset,
        )
        logs.append(
            f"基于 style={normalized_style_preset} 自动生成 expression_enhancements："
            f"{len(result['expression_enhancements'])} 项"
        )
    else:
        logs.append("text 不满足 expression_enhancements 自动生成条件，跳过")

    return result
