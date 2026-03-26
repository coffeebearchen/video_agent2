# -*- coding: utf-8 -*-
"""
字幕时间轴模块。

职责：
1. 计算句子级字幕时间轴
2. 基于文本长度分配时间
3. 返回带 start/end 的新 segments 列表
"""


def get_segment_text_length(segment):
	"""
	读取 segment 文本长度。
	
	若文本为空，返回最小保底长度 1，避免分到 0 秒。
	"""
	if not isinstance(segment, dict):
		return 1

	text = str(segment.get("text", "") or "").strip()
	return max(len(text), 1)


def has_complete_segment_times(segments):
	"""
	检查所有 segment 是否都已有完整 start/end。
	"""
	if not isinstance(segments, list) or not segments:
		return False

	for segment in segments:
		if not isinstance(segment, dict):
			return False
		if segment.get("start") is None or segment.get("end") is None:
			return False

	return True


def build_weighted_subtitle_timeline(segments, total_duration):
	"""
	按文本长度权重为 segments 分配时间。
	
	返回新的 segments 列表，不修改原对象。
	最后一个 end 严格对齐 total_duration。
	"""
	if not isinstance(segments, list) or not segments:
		return []

	try:
		total_duration = float(total_duration)
	except (TypeError, ValueError):
		return []

	if total_duration <= 0:
		return []

	weights = [get_segment_text_length(segment) for segment in segments]
	total_weight = sum(weights)
	if total_weight <= 0:
		return []

	result = []
	current_time = 0.0

	for index, segment in enumerate(segments):
		segment_data = dict(segment) if isinstance(segment, dict) else {}

		if index == len(segments) - 1:
			start_time = round(current_time, 3)
			end_time = round(total_duration, 3)
		else:
			segment_duration = total_duration * (weights[index] / total_weight)
			start_time = round(current_time, 3)
			end_time = round(current_time + segment_duration, 3)

			if end_time < start_time:
				end_time = start_time

		segment_data["start"] = start_time
		segment_data["end"] = end_time
		result.append(segment_data)
		current_time = end_time

	if result:
		result[-1]["end"] = round(total_duration, 3)
		if result[-1]["end"] < result[-1]["start"]:
			result[-1]["end"] = result[-1]["start"]

	return result