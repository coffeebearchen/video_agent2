# -*- coding: utf-8 -*-
"""
timing_engine.py

【Timing Engine V2｜Audio-Aware版】

职责：
1. 读取 element_plan.json
2. 为每个 scene 补出最小时间骨架
3. 支持音频驱动的场景时长
4. 输出 timing_plan.json
5. 输出下游兼容的 data/current/timing_plan.json

【特性说明】
- 本模块处理 ELEMENT → TIMING
- V2 增强：支持 scene.audio 音频文件驱动时长
- segments 支持自动平均切分
- 时长优先级：segment显式时间 > audio时长 > scene原duration > 默认duration
- 不做逐字时间轴
- 不做复杂音频识别
- 不做动画时序
"""

import json
from pathlib import Path
from modules.audio_utils import get_audio_duration
from modules.subtitle_timeline import (
	build_weighted_subtitle_timeline,
	has_complete_segment_times,
)


BASE_DIR = Path(__file__).resolve().parent
ROOT_ELEMENT_PLAN_FILE = BASE_DIR / "element_plan.json"
DATA_CURRENT_ELEMENT_PLAN_FILE = BASE_DIR / "data" / "current" / "element_plan.json"
ROOT_TIMING_PLAN_FILE = BASE_DIR / "timing_plan.json"
DATA_CURRENT_DIR = BASE_DIR / "data" / "current"
DATA_CURRENT_TIMING_PLAN_FILE = DATA_CURRENT_DIR / "timing_plan.json"


def load_element_plan():
    """读取 element_plan.json，兼容 list 与 {'scenes': [...]} 两种结构。"""
    input_file = None

    if ROOT_ELEMENT_PLAN_FILE.exists():
        input_file = ROOT_ELEMENT_PLAN_FILE
    elif DATA_CURRENT_ELEMENT_PLAN_FILE.exists():
        input_file = DATA_CURRENT_ELEMENT_PLAN_FILE
    else:
        raise FileNotFoundError(
            f"element_plan.json 不存在：{ROOT_ELEMENT_PLAN_FILE} 或 {DATA_CURRENT_ELEMENT_PLAN_FILE}"
        )

    with open(input_file, "r", encoding="utf-8") as file:
        data = json.load(file)

    if isinstance(data, list):
        scenes = data
    elif isinstance(data, dict):
        scenes = data.get("scenes", [])
    else:
        scenes = []

    if not isinstance(scenes, list):
        scenes = []

    return scenes, input_file


def get_default_duration(scene_type):
    """根据 scene type 返回固定时长。"""
    normalized_type = str(scene_type or "").strip().lower()

    if normalized_type == "overlay":
        return 4.0
    if normalized_type == "explain":
        return 5.0
    if normalized_type == "card":
        return 4.0
    return 4.0


def get_scene_base_duration(scene, default_duration):
	"""
	获取 scene 的原始 duration 字段。
	
	参数：
	- scene: scene dict
	- default_duration: 默认时长
	
	返回：
	- float: scene 原始 duration，若非法则返回 default_duration
	"""
	if not isinstance(scene, dict):
		return default_duration
	
	duration_value = scene.get("duration")
	if duration_value is None:
		return default_duration
	
	try:
		duration = float(duration_value)
		if duration > 0:
			return duration
	except (ValueError, TypeError):
		pass
	
	return default_duration


def get_scene_audio_duration(scene):
	"""
	如果 scene 有 audio.file，读取音频时长。
	
	参数：
	- scene: scene dict
	
	返回：
	- float: 音频时长（秒）。若无音频或失败，返回 0.0
	
	【设计说明】
	- 检查 scene.audio.file 是否存在且有效
	- 调用 audio_utils.get_audio_duration() 读取时长
	- 异常时返回 0.0
	"""
	if not isinstance(scene, dict):
		return 0.0
	
	audio_config = scene.get("audio")
	if not isinstance(audio_config, dict):
		return 0.0
	
	audio_file = audio_config.get("file")
	if not audio_file:
		return 0.0
	
	# 调用 audio_utils 读取时长
	audio_duration = get_audio_duration(str(audio_file).strip())
	return audio_duration


def get_segments_explicit_duration(segments):
	"""
	如果所有 segments 都有显式时间，返回该时间轴覆盖的总时长。
	"""
	if not has_complete_segment_times(segments):
		return 0.0

	try:
		start_values = [float(segment.get("start", 0.0)) for segment in segments]
		end_values = [float(segment.get("end", 0.0)) for segment in segments]
	except (TypeError, ValueError):
		return 0.0

	if not end_values:
		return 0.0

	timeline_duration = max(end_values) - min(start_values)
	if timeline_duration <= 0:
		return 0.0

	return round(timeline_duration, 3)


def build_average_segments(segments, total_duration):
	"""
	平均切分 segments，作为字幕加权失败时的兜底方案。
	"""
	if not isinstance(segments, list):
		return []

	if len(segments) == 0:
		return []

	segment_duration = total_duration / len(segments) if len(segments) > 0 else total_duration
	normalized = []
	current_time = 0.0

	for index, segment in enumerate(segments):
		segment_data = dict(segment) if isinstance(segment, dict) else {}
		start_time = round(current_time, 3)
		if index == len(segments) - 1:
			end_time = round(total_duration, 3)
		else:
			end_time = round(current_time + segment_duration, 3)

		segment_data["start"] = start_time
		segment_data["end"] = end_time
		normalized.append(segment_data)
		current_time = end_time

	return normalized


def normalize_segments(segments, total_duration):
	"""
	标准化 segments，补充 start/end 时间。
	
	规则：
	1. 如果 segments 为空，返回空列表
	2. 如果所有 segment 都有 start 和 end，原样返回
	3. 否则，优先按文本长度加权分配时间
	4. 若加权失败，再回退到平均切分
	
	参数：
	- segments: segment 列表
	- total_duration: 场景总时长
	
	返回：
	- list: 补充 start/end 后的 segments
	
	【设计说明】
	- 保留已有的 start/end，不覆盖
	- 缺少 start/end 的 segment 按数量平均分配时间
	- 避免时间重叠或留空
	"""
	if not isinstance(segments, list):
		return []
	
	if len(segments) == 0:
		return []
	
	if has_complete_segment_times(segments):
		# 所有 segment 都有 start/end，原样返回
		return segments

	weighted_segments = build_weighted_subtitle_timeline(segments, total_duration)
	if weighted_segments:
		return weighted_segments

	return build_average_segments(segments, total_duration)


def build_timing_for_scene(scene, default_duration=3.0):
	"""
	为单个 scene 构建时间配置。
	
	参数：
	- scene: scene dict
	- default_duration: 默认时长
	
	返回：
	- dict: 处理后的 scene（包含 scene_duration 和标准化后的 segments）
	
	【处理流程】
	1. 获取 scene 原始 duration
	2. 读取 audio 时长（若存在）
	3. 应用优先级：audio时长 > 原duration > 默认duration
	4. 写回 scene_duration
	5. 标准化 segments（平均切分）
	6. 返回处理后的 scene
	"""
	if not isinstance(scene, dict):
		scene = {}
	else:
		scene = dict(scene)  # 复制，避免修改原对象
	
	# 1. 获取原始 duration
	base_duration = get_scene_base_duration(scene, default_duration)
	segments = scene.get("segments", [])
	segments_duration = get_segments_explicit_duration(segments)
	
	# 2. 读取 audio 时长
	audio_duration = get_scene_audio_duration(scene)
	
	# 3. 应用优先级：segment显式时间 > audio时长 > 原duration > 默认duration
	if segments_duration > 0:
		scene_duration = segments_duration
	elif audio_duration > 0:
		scene_duration = audio_duration
	else:
		scene_duration = base_duration
	
	# 4. 写回 scene_duration
	scene["scene_duration"] = round(scene_duration, 3)
	
	# 5. 标准化 segments
	if isinstance(segments, list):
		normalized_segments = normalize_segments(segments, scene_duration)
		scene["segments"] = normalized_segments
	else:
		scene["segments"] = []
	
	return scene


def build_timing(scenes, default_duration=3.0):
	"""
	批量处理 scenes，为每个 scene 构建时间配置。
	
	参数：
	- scenes: scene 列表
	- default_duration: 默认时长
	
	返回：
	- list: 处理后的 scenes 列表
	"""
	if not isinstance(scenes, list):
		return []
	
	timing_scenes = []
	for scene in scenes:
		processed_scene = build_timing_for_scene(scene, default_duration)
		timing_scenes.append(processed_scene)
	
	return timing_scenes


def build_timing_plan(scenes):
	"""
	遍历 scenes，计算 duration / start_time / end_time。
	
	【增强说明】
	- V2 支持音频驱动的场景时长
	- 先执行 build_timing 进行场景级别的处理
	- 然后编译成 timing_plan 格式
	"""
	# 先通过 build_timing 处理每个 scene（支持音频）
	timing_scenes = build_timing(scenes)
	
	timing_plan = []
	current_time = 0.0
	
	for index, scene in enumerate(timing_scenes):
		if not isinstance(scene, dict):
			scene = {}
		
		scene_id = scene.get("scene_id", index)
		role = str(scene.get("role", "") or "")
		scene_type = str(scene.get("type", "") or "")
		text = str(scene.get("text", "") or "")
		
		# 获取已处理的 scene_duration（已支持音频）
		scene_duration = scene.get("scene_duration")
		if scene_duration is None:
			scene_duration = get_default_duration(scene_type)
		else:
			try:
				scene_duration = float(scene_duration)
			except (ValueError, TypeError):
				scene_duration = get_default_duration(scene_type)
		
		# 确保 duration 有效
		if scene_duration <= 0:
			scene_duration = get_default_duration(scene_type)
		
		start_time = round(current_time, 3)
		end_time = round(start_time + scene_duration, 3)
		
		timing_plan_item = {
			"scene_id": scene_id,
			"role": role,
			"type": scene_type,
			"text": text,
			"duration": round(scene_duration, 3),
			"start_time": start_time,
			"end_time": end_time,
		}
		
		# 保留 segments（已标准化）
		if "segments" in scene:
			timing_plan_item["segments"] = scene["segments"]
		
		timing_plan.append(timing_plan_item)
		current_time = end_time
	
	total_duration = round(current_time, 3)
	return timing_plan, total_duration


def save_timing_plan(timing_plan, total_duration):
    """写入根目录与下游兼容的 timing_plan.json。"""
    DATA_CURRENT_DIR.mkdir(parents=True, exist_ok=True)

    with open(ROOT_TIMING_PLAN_FILE, "w", encoding="utf-8") as file:
        json.dump(timing_plan, file, ensure_ascii=False, indent=2)

    downstream_output = {
        "scenes": timing_plan,
        "total_duration": total_duration,
    }
    with open(DATA_CURRENT_TIMING_PLAN_FILE, "w", encoding="utf-8") as file:
        json.dump(downstream_output, file, ensure_ascii=False, indent=2)


def main():
    print("=" * 60)
    print("开始生成 Timing Engine V1...")
    print("=" * 60)

    scenes, input_file = load_element_plan()
    print(f"已读取 element_plan.json：{input_file}")

    timing_plan, total_duration = build_timing_plan(scenes)
    save_timing_plan(timing_plan, total_duration)

    print(f"已生成 timing_plan.json：{ROOT_TIMING_PLAN_FILE}")
    print(f"已生成下游兼容 timing_plan.json：{DATA_CURRENT_TIMING_PLAN_FILE}")
    print(f"场景数量：{len(timing_plan)}")
    print(f"总时长：{total_duration:.1f} 秒")
    print("=" * 60)


if __name__ == "__main__":
    main()
