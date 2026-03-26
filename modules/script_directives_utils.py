# -*- coding: utf-8 -*-
"""
文件名：script_directives_utils.py
作用说明：
1. 提供 script_directives 的参数清洗工具
2. 提供插图路径补全工具
3. 提供多插图自动时间分布工具

设计原则：
1. 只做规则型清洗，不做 AI / NLP
2. 只服务于 SCRIPT -> SCENE 控制入口
3. 不改渲染层消费协议
"""

from __future__ import annotations

from pathlib import PureWindowsPath


DEFAULT_INSERT_DIR = "assets/inserts"
DEFAULT_INSERT_DURATION = 1.0
MIN_INSERT_DURATION = 0.2
MAX_INSERT_DURATION = 10.0

DEFAULT_INSERT_SCALE = 0.2
MIN_INSERT_SCALE = 0.05
MAX_INSERT_SCALE = 1.0

DEFAULT_SCENE_REFERENCE_DURATION = 4.0
DEFAULT_HEAD_PADDING = 0.4
DEFAULT_TAIL_PADDING = 0.4
MIN_USABLE_WINDOW = 0.5

SAFE_INSERT_POSITIONS = {
    "center",
    "top",
    "bottom",
    "left",
    "right",
    "top_left",
    "top_right",
    "bottom_left",
    "bottom_right",
}
RENDER_SAFE_INSERT_POSITIONS = {"top", "center", "bottom"}
SAFE_ENHANCEMENT_POSITIONS = {"top", "center", "bottom"}


def clean_text(text_value):
    """清洗文本；空文本返回空字符串。"""
    return str(text_value or "").strip()


def clean_float(value, default_value, min_value=None, max_value=None):
    """将输入稳定转换为 float，非法时回退默认值。"""
    try:
        result = float(value)
    except (TypeError, ValueError):
        result = float(default_value)

    if min_value is not None and result < min_value:
        result = float(default_value)
    if max_value is not None and result > max_value:
        result = float(default_value)

    return float(result)


def clean_optional_float(value, min_value=None):
    """将输入转为可选 float；非法时返回 None。"""
    if value is None:
        return None

    try:
        result = float(value)
    except (TypeError, ValueError):
        return None

    if min_value is not None and result < min_value:
        return None

    return float(result)


def clean_duration(value, default_value=DEFAULT_INSERT_DURATION):
    """清洗 duration，限定范围 0.2 ~ 10.0。"""
    return clean_float(
        value,
        default_value=default_value,
        min_value=MIN_INSERT_DURATION,
        max_value=MAX_INSERT_DURATION,
    )


def clean_scale(value, default_value=DEFAULT_INSERT_SCALE):
    """清洗 scale，限定范围 0.05 ~ 1.0。"""
    return clean_float(
        value,
        default_value=default_value,
        min_value=MIN_INSERT_SCALE,
        max_value=MAX_INSERT_SCALE,
    )


def clean_insert_position(position_value):
    """清洗插图 position，并收敛到当前渲染层安全值。"""
    position = clean_text(position_value).lower() or "center"
    if position not in SAFE_INSERT_POSITIONS:
        return "center", True

    if position in RENDER_SAFE_INSERT_POSITIONS:
        return position, False

    return "center", False


def clean_enhancement_position(position_value):
    """清洗强调 position。"""
    position = clean_text(position_value).lower() or "center"
    if position not in SAFE_ENHANCEMENT_POSITIONS:
        return "center", True

    return position, False


def resolve_insert_file_path(file_value):
    """规范化插图路径字符串，不做文件是否存在校验。"""
    normalized_file = clean_text(file_value)
    if not normalized_file:
        return "", None

    is_windows_absolute = PureWindowsPath(normalized_file).is_absolute()
    is_posix_absolute = normalized_file.startswith("/")
    if is_windows_absolute or is_posix_absolute:
        return normalized_file, None

    if "/" in normalized_file or "\\" in normalized_file:
        return normalized_file, None

    resolved = f"{DEFAULT_INSERT_DIR}/{normalized_file}"
    return resolved, f"插图 file 简写补全：{normalized_file} -> {resolved}"


def _normalize_insert_times(insert_item, scene_duration, logs, index):
    """清洗单条插图的时间字段。"""
    item = dict(insert_item)
    duration = clean_duration(item.get("duration"), default_value=DEFAULT_INSERT_DURATION)
    if item.get("duration") is None:
        logs.append(f"插图第 {index} 条未提供 duration，已使用默认值 {DEFAULT_INSERT_DURATION:.1f}")
    elif duration != clean_optional_float(item.get("duration"), min_value=MIN_INSERT_DURATION):
        logs.append(f"插图第 {index} 条 duration 非法，已回退默认值 {DEFAULT_INSERT_DURATION:.1f}")

    start_time = clean_optional_float(item.get("start"), min_value=0.0)
    if item.get("start") is not None and start_time is None:
        logs.append(f"插图第 {index} 条 start 非法，已视为未提供")

    end_time = clean_optional_float(item.get("end"), min_value=0.0)
    if item.get("end") is not None and end_time is None:
        logs.append(f"插图第 {index} 条 end 非法，已视为未提供")

    item["duration"] = duration
    item["start"] = start_time
    item["end"] = end_time

    if start_time is not None:
        final_end = end_time
        if final_end is None or final_end <= start_time:
            final_end = start_time + duration

        if final_end > scene_duration:
            final_end = scene_duration

        if final_end <= start_time:
            logs.append(f"忽略插图第 {index} 条：显式时间裁切后 end <= start")
            return None

        item["start"] = round(start_time, 3)
        item["end"] = round(final_end, 3)
        item.pop("duration", None)

    return item


def distribute_insert_timings(inserts, scene_duration, logs=None):
    """为插图分配稳定、可预测的 start/end。"""
    if logs is None:
        logs = []

    if not isinstance(inserts, list) or not inserts:
        return []

    cleaned_inserts = []
    for index, insert_item in enumerate(inserts, start=1):
        normalized_item = _normalize_insert_times(insert_item, scene_duration, logs, index)
        if normalized_item is not None:
            cleaned_inserts.append(normalized_item)

    auto_indexes = [index for index, item in enumerate(cleaned_inserts) if item.get("start") is None]
    if auto_indexes:
        head_padding = DEFAULT_HEAD_PADDING
        tail_padding = DEFAULT_TAIL_PADDING
        usable_window = max(scene_duration - head_padding - tail_padding, MIN_USABLE_WINDOW)
        total_count = len(cleaned_inserts)
        if total_count == 1:
            ordered_slots = [round(head_padding + usable_window / 2, 3)]
        else:
            step = usable_window / max(total_count - 1, 1)
            ordered_slots = [round(head_padding + step * index, 3) for index in range(total_count)]

        for auto_index in auto_indexes:
            start_time = ordered_slots[auto_index]
            item = cleaned_inserts[auto_index]
            duration = float(item.get("duration", DEFAULT_INSERT_DURATION))
            end_time = round(min(start_time + duration, scene_duration), 3)
            if end_time <= start_time:
                logs.append(f"忽略插图第 {auto_index + 1} 条：自动分布后 end <= start")
                item["ignore"] = True
                continue

            item["start"] = round(start_time, 3)
            item["end"] = end_time
            logs.append(
                f"自动分布插图时间：第 {auto_index + 1} 条 start={item['start']:.2f} end={item['end']:.2f}"
            )

    result = []
    for item in cleaned_inserts:
        if item.get("ignore"):
            continue

        start_time = item.get("start")
        end_time = item.get("end")
        if start_time is None or end_time is None or end_time <= start_time:
            continue

        item = dict(item)
        item["start"] = round(float(start_time), 3)
        item["end"] = round(float(end_time), 3)
        item.pop("duration", None)
        item.pop("ignore", None)
        result.append(item)

    return result
