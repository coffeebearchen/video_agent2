# -*- coding: utf-8 -*-
"""
文件名：script_directives_parser.py
作用说明：
1. 从 SCRIPT 文案中解析固定格式的控制指令
2. 将指令转换为 visual_inserts / expression_enhancements 结构
3. 返回清洗后的展示文案，避免控制指令进入渲染文本

设计边界：
1. 只支持严格格式：【指令 key=value key=value】
2. 不做自然语言理解
3. 不做模糊匹配
4. 非法格式直接忽略，不中断主流程
"""

from __future__ import annotations

import re

from modules.script_directives_utils import (
    DEFAULT_INSERT_DURATION,
    DEFAULT_SCENE_REFERENCE_DURATION,
    clean_duration,
    clean_enhancement_position,
    clean_insert_position,
    clean_scale,
    clean_text,
    clean_optional_float,
    distribute_insert_timings,
    resolve_insert_file_path,
)


DIRECTIVE_PATTERN = re.compile(r"【([^】]+)】")

SUPPORTED_INSERT_POSITIONS = {"center", "top", "bottom", "left", "right"}
SUPPORTED_ENHANCEMENT_POSITIONS = {"top", "center", "bottom"}

DEFAULT_ENHANCEMENT_TYPE = "popup"


def _normalize_text_for_display(text):
    """清理解析后的展示文案，避免留下多余空白。"""
    normalized_text = re.sub(r"[ \t]+", " ", str(text or ""))
    normalized_text = re.sub(r"\n\s+", "\n", normalized_text)
    normalized_text = re.sub(r"\n{3,}", "\n\n", normalized_text)
    return normalized_text.strip()


def _parse_key_value_tokens(tokens):
    """将 key=value token 列表解析为 dict；若任一 token 非法则整体失败。"""
    parsed = {}
    for token in tokens:
        if token.count("=") != 1:
            return None

        key, value = token.split("=", 1)
        key = str(key or "").strip().lower()
        value = str(value or "").strip()
        if not key or not value:
            return None

        parsed[key] = value

    return parsed


def _parse_visual_insert_directive(arguments):
    """解析插图指令并转换为 visual_inserts 结构。"""
    log_messages = []
    file_value, path_log = resolve_insert_file_path(arguments.get("file"))
    if not file_value:
        return None, ["忽略插图指令：file 为空或非法"]

    if path_log:
        log_messages.append(path_log)

    raw_duration = arguments.get("duration")
    duration = clean_duration(raw_duration, default_value=DEFAULT_INSERT_DURATION)
    if raw_duration is not None:
        raw_duration_float = clean_optional_float(raw_duration, min_value=0.0)
        if raw_duration_float is None or abs(raw_duration_float - duration) > 1e-9:
            log_messages.append(f"duration 非法，已回退默认值 {DEFAULT_INSERT_DURATION:.1f}")
    else:
        log_messages.append(f"未提供 duration，已使用默认值 {DEFAULT_INSERT_DURATION:.1f}")

    raw_scale = arguments.get("scale")
    scale = clean_scale(raw_scale)
    if raw_scale is not None:
        raw_scale_float = clean_optional_float(raw_scale, min_value=0.0)
        if raw_scale_float is None or abs(raw_scale_float - scale) > 1e-9:
            log_messages.append("scale 非法，已回退默认值 0.2")
    else:
        log_messages.append("未提供 scale，已使用默认值 0.2")

    position, position_fallback = clean_insert_position(arguments.get("position"))
    if position_fallback:
        log_messages.append("position 非法，已回退 center")

    start_time = clean_optional_float(arguments.get("start"), min_value=0.0)
    if arguments.get("start") is not None and start_time is None:
        log_messages.append("start 非法，已视为未提供")

    end_time = clean_optional_float(arguments.get("end"), min_value=0.0)
    if arguments.get("end") is not None and end_time is None:
        log_messages.append("end 非法，已视为未提供")

    return {
        "type": "image",
        "file": file_value,
        "path": file_value,
        "duration": round(duration, 3),
        "start": start_time,
        "end": end_time,
        "position": position,
        "scale": scale,
    }, log_messages


def _parse_expression_directive(arguments):
    """解析强调指令并转换为 expression_enhancements 结构。"""
    text_value = clean_text(arguments.get("text"))
    if not text_value:
        return None, ["忽略强调指令：text 为空"]

    start_time = clean_optional_float(arguments.get("start"), min_value=0.0)
    end_time = clean_optional_float(arguments.get("end"), min_value=0.0)
    if start_time is None or end_time is None:
        return None, ["忽略强调指令：start/end 非法或缺失"]

    if end_time <= start_time:
        return None, ["忽略强调指令：end <= start"]

    position, position_fallback = clean_enhancement_position(arguments.get("position"))
    log_messages = []
    if position_fallback:
        log_messages.append("强调 position 非法，已回退 center")

    return {
        "type": DEFAULT_ENHANCEMENT_TYPE,
        "text": text_value,
        "start": round(start_time, 3),
        "end": round(end_time, 3),
        "position": position,
    }, log_messages


def parse_single_directive(directive_content):
    """解析单条指令；仅成功时返回结构化结果。"""
    content = str(directive_content or "").strip()
    if not content:
        return None, []

    tokens = content.split()
    if len(tokens) < 2:
        return None, []

    directive_name = str(tokens[0] or "").strip()
    arguments = _parse_key_value_tokens(tokens[1:])
    if arguments is None:
        return None, []

    if directive_name == "插图":
        visual_insert, log_messages = _parse_visual_insert_directive(arguments)
        if visual_insert is None:
            return None, log_messages

        return {
            "directive_type": "visual_insert",
            "payload": visual_insert,
        }, log_messages

    if directive_name == "强调":
        enhancement, log_messages = _parse_expression_directive(arguments)
        if enhancement is None:
            return None, log_messages

        return {
            "directive_type": "expression_enhancement",
            "payload": enhancement,
        }, log_messages

    return None, []


def _build_empty_result(source_text):
    """构建统一返回结构。"""
    cleaned_text = _normalize_text_for_display(source_text)
    return {
        "text": cleaned_text,
        "visual_inserts": [],
        "expression_enhancements": [],
        "stats": {
            "total_directives": 0,
            "valid_visual_inserts": 0,
            "valid_expression_enhancements": 0,
            "ignored_directives": 0,
        },
        "ignored_details": [],
        "logs": [],
    }


def parse_script_directives(text, scene_duration=DEFAULT_SCENE_REFERENCE_DURATION):
    """解析文案中的全部控制指令，并返回清洗后的展示文案。"""
    source_text = str(text or "")
    if not source_text:
        return _build_empty_result(source_text)

    visual_inserts = []
    expression_enhancements = []
    cleaned_segments = []
    ignored_details = []
    log_messages = ["开始解析 scene 文案控制指令"]
    last_index = 0
    total_directives = 0
    visual_directive_count = 0
    enhancement_directive_count = 0

    for match in DIRECTIVE_PATTERN.finditer(source_text):
        start_index, end_index = match.span()
        cleaned_segments.append(source_text[last_index:start_index])
        total_directives += 1

        raw_directive = match.group(1)
        parsed_directive, directive_logs = parse_single_directive(raw_directive)
        log_messages.extend(directive_logs)
        if parsed_directive is None:
            # 非法或不支持的格式保留原文，不做吞掉处理。
            cleaned_segments.append(match.group(0))
            ignored_details.append(
                {
                    "directive": match.group(0),
                    "reason": "格式非法、字段缺失或当前不支持",
                }
            )
        else:
            directive_type = parsed_directive.get("directive_type")
            payload = parsed_directive.get("payload")
            if directive_type == "visual_insert":
                visual_inserts.append(payload)
                visual_directive_count += 1
            elif directive_type == "expression_enhancement":
                expression_enhancements.append(payload)
                enhancement_directive_count += 1
            else:
                cleaned_segments.append(match.group(0))
                ignored_details.append(
                    {
                        "directive": match.group(0),
                        "reason": f"未知 directive_type: {directive_type}",
                    }
                )

        last_index = end_index

    cleaned_segments.append(source_text[last_index:])
    cleaned_text = _normalize_text_for_display("".join(cleaned_segments))
    log_messages.append(
        f"检测到插图指令 {visual_directive_count} 条，强调指令 {enhancement_directive_count} 条"
    )
    visual_inserts = distribute_insert_timings(visual_inserts, scene_duration=scene_duration, logs=log_messages)

    return {
        "text": cleaned_text,
        "visual_inserts": visual_inserts,
        "expression_enhancements": expression_enhancements,
        "stats": {
            "total_directives": total_directives,
            "valid_visual_inserts": len(visual_inserts),
            "valid_expression_enhancements": len(expression_enhancements),
            "ignored_directives": len(ignored_details),
        },
        "ignored_details": ignored_details,
        "logs": log_messages,
    }
