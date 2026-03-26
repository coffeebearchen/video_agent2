# -*- coding: utf-8 -*-
"""
表达增强层模块。

职责：
1. 解析 scene 中的 expression_enhancements
2. 清洗并标准化 enhancement 项
3. 生成可叠加到场景中的轻量文本 clips
"""

import importlib

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def _import_moviepy():
	"""兼容 MoviePy 新旧版本的导入方式。"""
	try:
		return importlib.import_module("moviepy.editor")
	except ModuleNotFoundError:
		return importlib.import_module("moviepy")


def _set_duration(clip, duration):
	"""兼容 MoviePy 新旧版本的时长设置方法。"""
	if hasattr(clip, "set_duration"):
		return clip.set_duration(duration)
	return clip.with_duration(duration)


def _set_start(clip, start_time):
	"""兼容 MoviePy 新旧版本的开始时间设置方法。"""
	if hasattr(clip, "set_start"):
		return clip.set_start(start_time)
	return clip.with_start(start_time)


def _set_position(clip, position):
	"""兼容 MoviePy 新旧版本的位置设置方法。"""
	if hasattr(clip, "set_position"):
		return clip.set_position(position)
	return clip.with_position(position)


def normalize_enhancement_item(item, scene_duration):
	"""
	检查并标准化单个 enhancement 项。
	"""
	if not isinstance(item, dict):
		return None

	enhancement_type = str(item.get("type", "") or "").strip().lower()
	if enhancement_type not in {"badge", "popup", "caption"}:
		return None

	text = str(item.get("text", "") or "").strip()
	if not text:
		return None

	try:
		start_time = float(item.get("start"))
		end_time = float(item.get("end"))
	except (TypeError, ValueError):
		return None

	start_time = max(0.0, start_time)
	end_time = min(float(scene_duration), end_time)
	if end_time <= start_time:
		return None

	default_positions = {
		"badge": "top",
		"popup": "center",
		"caption": "bottom",
	}
	position = str(item.get("position", "") or "").strip().lower()
	if position not in {"top", "center", "bottom"}:
		position = default_positions[enhancement_type]

	return {
		"type": enhancement_type,
		"text": text,
		"start": round(start_time, 3),
		"end": round(end_time, 3),
		"position": position,
	}


def normalize_expression_enhancements(scene, scene_duration):
	"""
	读取 scene["expression_enhancements"] 并返回合法项列表。
	"""
	if not isinstance(scene, dict):
		return []

	enhancements = scene.get("expression_enhancements")
	if not isinstance(enhancements, list):
		return []

	result = []
	for item in enhancements:
		normalized_item = normalize_enhancement_item(item, scene_duration)
		if normalized_item is not None:
			result.append(normalized_item)

	return result


def _load_font(font_size, runtime_config):
	"""尽量加载可用字体，失败则回退到默认字体。"""
	candidates = ["DejaVuSans.ttf"]

	ui_card = getattr(runtime_config, "ui_card", None)
	if ui_card is not None:
		candidates.extend(getattr(ui_card, "project_font_candidates", ()) or ())
		candidates.extend(getattr(ui_card, "windows_font_candidates", ()) or ())

	for candidate in candidates:
		try:
			return ImageFont.truetype(str(candidate), font_size)
		except Exception:
			continue

	return ImageFont.load_default()


def _get_style_config(item_type):
	"""返回不同 enhancement 类型的样式参数。"""
	if item_type == "badge":
		return {
			"font_size": 42,
			"fill": (255, 238, 170, 255),
			"background": (22, 22, 28, 210),
			"border": (255, 210, 90, 220),
			"padding_x": 28,
			"padding_y": 16,
		}
	if item_type == "popup":
		return {
			"font_size": 50,
			"fill": (255, 255, 255, 255),
			"background": (16, 16, 24, 188),
			"border": (120, 200, 255, 200),
			"padding_x": 34,
			"padding_y": 20,
		}
	return {
		"font_size": 38,
		"fill": (238, 242, 255, 255),
		"background": (8, 8, 12, 184),
		"border": (160, 160, 180, 180),
		"padding_x": 24,
		"padding_y": 14,
	}


def _resolve_position(item, width, height):
	"""计算 enhancement 的安全位置。"""
	position = item.get("position")
	if position == "top":
		return ("center", int(height * 0.12))
	if position == "center":
		return ("center", int(height * 0.30))
	return ("center", int(height * 0.58))


def build_enhancement_text_clip(item, width, height, runtime_config):
	"""
	为单个 enhancement 项构建文本 clip。
	"""
	try:
		moviepy_module = _import_moviepy()
		ImageClip = moviepy_module.ImageClip
	except Exception as error:
		print(f"[expression_enhancer] MoviePy 导入失败: {error}")
		return None

	style = _get_style_config(item.get("type"))
	font = _load_font(style["font_size"], runtime_config)
	text = item.get("text", "")

	try:
		dummy_image = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
		draw = ImageDraw.Draw(dummy_image)
		text_bbox = draw.textbbox((0, 0), text, font=font)
		text_width = max(text_bbox[2] - text_bbox[0], 1)
		text_height = max(text_bbox[3] - text_bbox[1], 1)
	except Exception as error:
		print(f"[expression_enhancer] 文本尺寸计算失败: {error}")
		return None

	padding_x = style["padding_x"]
	padding_y = style["padding_y"]
	clip_width = min(text_width + padding_x * 2, int(width * 0.84))
	clip_height = text_height + padding_y * 2

	try:
		image = Image.new("RGBA", (clip_width, clip_height), (0, 0, 0, 0))
		draw = ImageDraw.Draw(image)
		draw.rounded_rectangle(
			[(0, 0), (clip_width - 1, clip_height - 1)],
			radius=18,
			fill=style["background"],
			outline=style["border"],
			width=2,
		)
		draw.text((padding_x, padding_y), text, font=font, fill=style["fill"])
		clip = ImageClip(np.array(image))
	except Exception as error:
		print(f"[expression_enhancer] 文本 clip 构建失败: {error}")
		return None

	duration = round(item["end"] - item["start"], 3)
	if duration <= 0:
		return None

	position = _resolve_position(item, width, height)
	try:
		clip = _set_duration(clip, duration)
		clip = _set_start(clip, item["start"])
		clip = _set_position(clip, position)
		return clip
	except Exception as error:
		print(f"[expression_enhancer] clip 参数设置失败: {error}")
		return None


def build_expression_enhancement_clips(scene, scene_duration, width, height, runtime_config):
	"""
	生成当前 scene 的全部 enhancement clips。
	"""
	normalized_items = normalize_expression_enhancements(scene, scene_duration)
	if not normalized_items:
		return []

	clips = []
	for item in normalized_items:
		clip = build_enhancement_text_clip(item, width, height, runtime_config)
		if clip is not None:
			clips.append(clip)

	return clips