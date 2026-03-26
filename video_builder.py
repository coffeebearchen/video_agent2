# -*- coding: utf-8 -*-
"""
文件名：video_builder.py
作用说明：
1. 读取 compiled_plan.json
2. 按 scene 生成背景层、中间视觉插入层与信息卡片层
3. 拼接整条视频
4. 输出到固定 mp4 路径

本次改动点：
1. 补充 MoviePy 新旧版本导入兼容
2. 补充主流程 clip 常用方法的新旧 API 兼容
3. 新增视觉插入层集成（Task19）
4. 不改主链、不改 style 逻辑，只修当前运行环境兼容性
"""

import argparse
import importlib
import json
import shutil
from pathlib import Path

import numpy as np

try:
	_moviepy_module = importlib.import_module("moviepy.editor")
except ModuleNotFoundError:
	_moviepy_module = importlib.import_module("moviepy")

ColorClip = _moviepy_module.ColorClip
CompositeVideoClip = _moviepy_module.CompositeVideoClip
ImageClip = _moviepy_module.ImageClip
VideoFileClip = _moviepy_module.VideoFileClip
concatenate_videoclips = _moviepy_module.concatenate_videoclips
vfx = _moviepy_module.vfx

from asset_manager import get_background_asset_for_scene, get_image_for_scene
from modules.clip_layout import prepare_video_background_clip
from modules.config import build_runtime_config
from modules.expression_enhancer import build_expression_enhancement_clips
from modules.image_layout import prepare_background_image
from modules.motion_engine import build_motion_background_clip, choose_motion_mode, get_motion_canvas_size
from modules.segment_engine import build_segment_overlay_clips
from modules.style_presets import list_available_styles
from modules.user_asset_resolver import resolve_scene_priority_asset
from modules.visual_insert_engine import build_visual_insert_clips


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
DATA_CURRENT_DIR = BASE_DIR / "data" / "current"
ROOT_COMPILED_PLAN_FILE = BASE_DIR / "compiled_plan.json"
DATA_CURRENT_COMPILED_PLAN_FILE = DATA_CURRENT_DIR / "compiled_plan.json"
OUTPUT_VIDEO_FILE = OUTPUT_DIR / "video_builder_v1.mp4"
DATA_CURRENT_VIDEO_FILE = DATA_CURRENT_DIR / "video_builder_v1.mp4"


def _set_duration(clip, duration):
	"""兼容 MoviePy 新旧版本的时长设置方法。"""
	if hasattr(clip, "set_duration"):
		return clip.set_duration(duration)
	return clip.with_duration(duration)


def _set_position(clip, position):
	"""兼容 MoviePy 新旧版本的位置设置方法。"""
	if hasattr(clip, "set_position"):
		return clip.set_position(position)
	return clip.with_position(position)


def _set_fps(clip, fps):
	"""兼容 MoviePy 新旧版本的帧率设置方法。"""
	if hasattr(clip, "set_fps"):
		return clip.set_fps(fps)
	return clip.with_fps(fps)


def _apply_fadein(clip, duration):
	"""兼容 MoviePy 新旧版本的淡入效果。"""
	if hasattr(clip, "fx") and hasattr(vfx, "fadein"):
		return clip.fx(vfx.fadein, duration)
	return clip.with_effects([vfx.FadeIn(duration)])


def _apply_fadeout(clip, duration):
	"""兼容 MoviePy 新旧版本的淡出效果。"""
	if hasattr(clip, "fx") and hasattr(vfx, "fadeout"):
		return clip.fx(vfx.fadeout, duration)
	return clip.with_effects([vfx.FadeOut(duration)])


def register_clip(clip_registry, clip):
	"""注册需要在主流程结束后统一释放的 clip。"""
	if clip is None:
		return None

	clip_registry.append(clip)
	return clip


def close_registered_clips(clip_registry):
	"""按逆序统一释放 clip，避免依赖垃圾回收触发 __del__。"""
	closed_clip_ids = set()
	for clip in reversed(clip_registry):
		clip_id = id(clip)
		if clip_id in closed_clip_ids:
			continue

		closed_clip_ids.add(clip_id)
		try:
			clip.close()
		except Exception:
			pass


def parse_args():
	"""解析命令行参数。"""
	parser = argparse.ArgumentParser(description="VIDEO_AGENT Video Builder")
	parser.add_argument(
		"--style",
		default=None,
		help="可选风格预设，例如 serious / energetic / calm / minimal",
	)
	return parser.parse_args()


def load_compiled_plan():
	"""
	读取 compiled_plan.json，兼容多种结构。
	
	支持格式：
	1. list 格式（老格式）：[{...}, {...}]
	2. dict["scenes"] 格式：{"scenes": [...]}
	3. dict["template"] + ["scenes"] 格式：{"template": "...", "scenes": [...]}
	4. dict["style"] + ["scenes"] 格式：{"style": {...}, "scenes": [...]}
	
	返回：
	- (scenes, template, style_config, input_file)
	  scenes: scene 列表
	  template: 模板名称（若存在则是 str，否则是 None）
	  style_config: 顶层 style 配置（若存在则是 dict，否则是 None）
	  input_file: 读取的文件路径
	"""
	input_file = None

	if ROOT_COMPILED_PLAN_FILE.exists():
		input_file = ROOT_COMPILED_PLAN_FILE
	elif DATA_CURRENT_COMPILED_PLAN_FILE.exists():
		input_file = DATA_CURRENT_COMPILED_PLAN_FILE
	else:
		raise FileNotFoundError(
			f"compiled_plan.json 不存在：{ROOT_COMPILED_PLAN_FILE} 或 {DATA_CURRENT_COMPILED_PLAN_FILE}"
		)

	with open(input_file, "r", encoding="utf-8") as file:
		data = json.load(file)

	template = None
	style_config = None
	scenes = []

	if isinstance(data, list):
		# 格式1：直接 list
		scenes = data
		template = None
		style_config = None
	elif isinstance(data, dict):
		# 格式2 或 3：dict 格式
		scenes = data.get("scenes", [])
		template = data.get("template")
		style_candidate = data.get("style")
		if isinstance(style_candidate, dict):
			style_config = style_candidate
	else:
		scenes = []
		template = None
		style_config = None

	if not isinstance(scenes, list):
		scenes = []

	return scenes, template, style_config, input_file


def get_scene_duration(scene, runtime_config):
	"""读取并清洗 scene.duration。"""
	duration = scene.get("duration", runtime_config.video.default_duration)
	try:
		duration = float(duration)
	except (TypeError, ValueError):
		duration = runtime_config.video.default_duration

	if duration <= 0:
		duration = runtime_config.video.default_duration

	return duration


def get_fade_duration(duration, transition_config):
	"""返回简单、稳定、可解释的淡入淡出时长。"""
	fade_duration = duration * transition_config.base_fade_ratio
	fade_duration = max(fade_duration, transition_config.soft_min_fade_duration)
	fade_duration = min(fade_duration, transition_config.default_fade_duration)
	fade_duration = min(fade_duration, duration / 3)
	fade_duration = max(fade_duration, transition_config.hard_min_fade_duration)
	return fade_duration


def resolve_style_transition(runtime_config):
	"""读取并清洗 style.transition，保持旧配置兼容。"""
	style_transition = getattr(runtime_config, "style_transition", None)
	enabled = True
	transition_type = "fade"
	duration = 0.5

	if style_transition is not None:
		enabled = bool(getattr(style_transition, "enabled", True))
		transition_type = str(getattr(style_transition, "type", "fade") or "fade").strip().lower() or "fade"
		try:
			duration = float(getattr(style_transition, "duration", 0.5))
		except (TypeError, ValueError):
			duration = 0.5
	else:
		duration = get_fade_duration(runtime_config.video.default_duration, runtime_config.transition)

	if duration <= 0:
		duration = 0.5

	return enabled, transition_type, duration


def build_color_background_clip(duration, width, height, runtime_config):
	"""生成纯色 fallback 背景。"""
	return _set_duration(ColorClip(size=(width, height), color=runtime_config.video.background_color), duration)


def build_video_background_clip(scene_index, asset_path, duration, width, height, clip_registry):
	"""基于视频素材生成背景 clip。"""
	try:
		display_path = asset_path.relative_to(BASE_DIR)
	except ValueError:
		display_path = asset_path
	print(f"[video_builder] scene={scene_index} 使用视频背景: {display_path}")

	source_clip = register_clip(clip_registry, VideoFileClip(str(asset_path)))
	fitted_clip, duration_strategy = prepare_video_background_clip(source_clip, duration, width, height)
	fitted_clip = register_clip(clip_registry, fitted_clip)

	print(f"[video_builder] scene={scene_index} 视频时长策略: {duration_strategy}")
	print(f"[video_builder] scene={scene_index} 视频尺寸适配成功")
	return fitted_clip


def build_image_background_clip(scene_index, scene_type, text, image_path, duration, width, height, runtime_config):
	"""基于图片素材生成背景 clip。"""
	motion_width, motion_height = get_motion_canvas_size(width, height, runtime_config.motion)
	try:
		display_path = image_path.relative_to(BASE_DIR)
	except ValueError:
		display_path = image_path

	print(f"[video_builder] scene={scene_index} 使用图片背景: {display_path}")
	background_array = prepare_background_image(
		image_path,
		motion_width,
		motion_height,
		image_config=runtime_config.image_layout,
	)
	print(f"[video_builder] scene={scene_index} 图片背景处理成功：已完成按比例缩放、居中裁切与轻微暗化")

	motion_mode = choose_motion_mode(scene_index, scene_type, text, runtime_config.motion)
	try:
		background_clip = build_motion_background_clip(
			background_array=background_array,
			duration=duration,
			frame_width=width,
			frame_height=height,
			motion_mode=motion_mode,
			motion_config=runtime_config.motion,
		)
		print(f"[video_builder] scene={scene_index} 背景运动模式: {motion_mode}")
		return background_clip
	except Exception as error:
		print(f"[video_builder] scene={scene_index} 背景运动失败: {error}")
		print(f"[video_builder] scene={scene_index} 改用静态图片背景继续生成")
		return _set_position(_set_duration(ImageClip(background_array), duration), "center")


def build_background_clip(scene, scene_index, scene_type, text, duration, width, height, runtime_config, clip_registry):
	"""构建背景层，固定优先级：video > image > fallback color。"""
	priority_asset = resolve_scene_priority_asset(scene)
	if priority_asset is not None:
		asset_type = priority_asset.get("asset_type")
		asset_path = priority_asset.get("asset_path")
		asset_source = priority_asset.get("asset_source")

		if asset_source == "user_anchor":
			print(f"[video_builder] scene={scene_index} 使用用户即时素材")
		elif asset_source == "user_local_assets":
			print(f"[video_builder] scene={scene_index} 使用用户本地素材")

		if asset_type == "video" and asset_path:
			try:
				return build_video_background_clip(scene_index, asset_path, duration, width, height, clip_registry)
			except Exception as error:
				print(f"[video_builder] scene={scene_index} 用户视频素材处理失败: {asset_path}，原因: {error}")
				print(f"[video_builder] scene={scene_index} 回退系统素材")

		if asset_type == "image" and asset_path:
			try:
				background_clip = build_image_background_clip(
					scene_index,
					scene_type,
					text,
					asset_path,
					duration,
					width,
					height,
					runtime_config,
				)
				return register_clip(clip_registry, background_clip)
			except Exception as error:
				print(f"[video_builder] scene={scene_index} 用户图片素材处理失败: {asset_path}，原因: {error}")
				print(f"[video_builder] scene={scene_index} 回退系统素材")

	print(f"[video_builder] scene={scene_index} 回退系统素材")
	asset_info = get_background_asset_for_scene(scene_type)
	if asset_info is None:
		print(f"[video_builder] scene={scene_index} 无素材可用，使用纯色背景")
		return register_clip(clip_registry, build_color_background_clip(duration, width, height, runtime_config))

	asset_type = asset_info.get("asset_type")
	asset_path = asset_info.get("asset_path")
	if not asset_path:
		print(f"[video_builder] scene={scene_index} 素材路径无效，使用纯色背景")
		return register_clip(clip_registry, build_color_background_clip(duration, width, height, runtime_config))

	if asset_type == "video":
		try:
			return build_video_background_clip(scene_index, asset_path, duration, width, height, clip_registry)
		except Exception as error:
			print(f"[video_builder] scene={scene_index} 视频素材处理失败: {asset_path}，原因: {error}")
			print(f"[video_builder] scene={scene_index} 回退到图片背景")

	image_path = asset_path if asset_type == "image" else get_image_for_scene(scene_type)
	if image_path is not None:
		try:
			background_clip = build_image_background_clip(
				scene_index,
				scene_type,
				text,
				image_path,
				duration,
				width,
				height,
				runtime_config,
			)
			return register_clip(clip_registry, background_clip)
		except Exception as error:
			print(f"[video_builder] scene={scene_index} 图片素材处理失败: {image_path}，原因: {error}")
			print(f"[video_builder] scene={scene_index} 回退到纯色背景")

	print(f"[video_builder] scene={scene_index} 图片与视频均不可用，使用纯色背景")
	return register_clip(clip_registry, build_color_background_clip(duration, width, height, runtime_config))


def build_scene_clip(scene, scene_index, runtime_config, clip_registry):
	"""根据单个 scene 生成视频片段（包含背景层、视觉插入层、文字层）。"""
	if not isinstance(scene, dict):
		scene = {}

	width = runtime_config.video.width
	height = runtime_config.video.height
	fps = runtime_config.video.fps

	text = str(scene.get("text", "") or "")
	scene_type = str(scene.get("type", "") or "")
	duration = get_scene_duration(scene, runtime_config)

	# 1. 构建背景层
	background_clip = build_background_clip(
		scene=scene,
		scene_index=scene_index,
		scene_type=scene_type,
		text=text,
		duration=duration,
		width=width,
		height=height,
		runtime_config=runtime_config,
		clip_registry=clip_registry,
	)

	# 2. 构建中间视觉插入层（新增 Task19）
	insert_clips = build_visual_insert_clips(
		scene=scene,
		scene_duration=duration,
		width=width,
		height=height,
		runtime_config=runtime_config,
	)
	for insert_clip in insert_clips:
		register_clip(clip_registry, insert_clip)

	# 3. 构建文字表达层（segment overlay）
	overlay_clips = build_segment_overlay_clips(
		scene=scene,
		scene_duration=duration,
		width=width,
		height=height,
		runtime_config=runtime_config,
	)
	for overlay_clip in overlay_clips:
		register_clip(clip_registry, overlay_clip)

	# 4. 构建表达增强层（新增 Task24）
	enhancement_clips = build_expression_enhancement_clips(
		scene=scene,
		scene_duration=duration,
		width=width,
		height=height,
		runtime_config=runtime_config,
	)
	for enhancement_clip in enhancement_clips:
		register_clip(clip_registry, enhancement_clip)
	if enhancement_clips:
		print(f"[video_builder] scene={scene_index} expression enhancements = {len(enhancement_clips)}")

	# 5. 合成最终 scene clip：背景 + 视觉插入 + 文字 + 表达增强
	all_layers = [background_clip] + insert_clips + overlay_clips + enhancement_clips
	scene_clip = register_clip(
		clip_registry,
		_set_duration(CompositeVideoClip(all_layers, size=(width, height)), duration),
	)

	transition_enabled, transition_type, transition_duration = resolve_style_transition(runtime_config)
	if not transition_enabled:
		print(f"[video_builder] scene={scene_index} 转场已关闭")
		return _set_fps(scene_clip, fps)

	if transition_type != "fade":
		print("[video_builder] 当前仅支持 fade 转场，已回退到 fade")
		transition_type = "fade"

	if transition_type == "fade":
		scene_clip = _apply_fadeout(_apply_fadein(scene_clip, transition_duration), transition_duration)
		print(f"[video_builder] scene={scene_index} 已应用 fade 转场，时长 {transition_duration:.2f} 秒")

	return _set_fps(scene_clip, fps)


def build_video(scenes, runtime_config, clip_registry):
	"""遍历 scenes 并拼接最终视频。"""
	if not scenes:
		raise ValueError("compiled_plan 中 scenes 为空，无法生成视频")

	print("开始生成 scene clips...")
	scene_clips = [build_scene_clip(scene, index, runtime_config, clip_registry) for index, scene in enumerate(scenes)]
	print("正在拼接视频...")
	final_clip = concatenate_videoclips(scene_clips, method="compose")
	return register_clip(clip_registry, final_clip)


def save_video(final_clip, output_path, runtime_config):
	"""输出主视频，并尽力同步副本，不让副本失败阻断主流程。"""
	OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
	DATA_CURRENT_DIR.mkdir(parents=True, exist_ok=True)

	final_clip.write_videofile(
		str(output_path),
		fps=runtime_config.video.fps,
		codec="libx264",
		audio=False,
		preset="medium",
		threads=4,
	)
	print(f"[video_builder] 主视频输出成功: {output_path}")

	try:
		shutil.copyfile(output_path, DATA_CURRENT_VIDEO_FILE)
		print(f"[video_builder] 已同步副本: {DATA_CURRENT_VIDEO_FILE}")
	except Exception as error:
		print(f"[video_builder] 副本同步失败: {DATA_CURRENT_VIDEO_FILE}，原因: {error}")


def main():
	"""主入口：构建配置、读取计划、生成视频、保存输出。"""
	args = parse_args()
	
	# 先读取 compiled_plan 获取模板与 style 信息
	scenes_draft, template, style_config, input_file = load_compiled_plan()

	resolved_style_name = args.style
	if resolved_style_name is None and isinstance(style_config, dict):
		resolved_style_name = style_config.get("preset")
	
	# 构建 runtime_config，传入模板信息
	runtime_config = build_runtime_config(
		style_name=resolved_style_name,
		template_name=template,
		template_enabled=True,
		style_overrides=style_config,
	)
	all_clips_to_close = []

	print("开始生成 Video Builder V1...")
	if args.style and not runtime_config.style_found:
		print(
			f"[video_builder] 风格未命中: {runtime_config.requested_style}，"
			f"已回退到默认风格 {runtime_config.style_name}"
		)
	else:
		print(f"[video_builder] 当前风格预设: {runtime_config.style_name}")

	print(f"[video_builder] 可用风格: {', '.join(list_available_styles())}")
	print(f"[video_builder] transition enabled = {runtime_config.style_transition.enabled}")
	print(f"[video_builder] transition type = {runtime_config.style_transition.type}")
	print(f"[video_builder] transition duration = {runtime_config.style_transition.duration:.2f}")
	
	print(f"已读取 compiled_plan.json：{input_file}")
	
	if runtime_config.template.template_name:
		print(f"[video_builder] template = {runtime_config.template.template_name}")

	final_clip = None
	try:
		final_clip = build_video(scenes_draft, runtime_config, all_clips_to_close)
		save_video(final_clip, OUTPUT_VIDEO_FILE, runtime_config)
	finally:
		close_registered_clips(all_clips_to_close)

	total_duration = sum(get_scene_duration(scene, runtime_config) for scene in scenes_draft if isinstance(scene, dict))
	print(f"已输出视频：{OUTPUT_VIDEO_FILE}")
	print(f"总场景数：{len(scenes_draft)}")
	print(f"总时长：{total_duration:.1f} 秒")


if __name__ == "__main__":
	main()
