# -*- coding: utf-8 -*-
"""
文件名：visual_insert_engine.py
作用说明：
1. 解析 scene 中的 visual_inserts 字段
2. 清洗和校验视觉插入数据
3. 为每个合法 insert 构建 ImageClip
4. 返回可直接合成到 scene 的 insert clip 列表

本次改动点（TASK19-A 工程收敛修复）：
1. 统一 start/end 时间清洗：normalize_time_range 单一出口
2. 调整位置计算避免压住底部 UI 卡片
3. 完善图片缩放保持宽高比的处理
4. 确保 fade_in 参数从 config 读取，不硬编码
5. 确保 visual_insert_enabled 开关真实生效
6. 完善过程中的打印与错误处理，确保不炸主流程
"""

import importlib
from pathlib import Path

from modules.template_presets import (
	get_template_role_defaults,
	validate_template_role,
)


def _import_moviepy():
	"""兼容 MoviePy 新旧版本的导入方式。"""
	try:
		_moviepy_module = importlib.import_module("moviepy.editor")
	except ModuleNotFoundError:
		_moviepy_module = importlib.import_module("moviepy")
	
	return _moviepy_module


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


def _apply_fadein(clip, duration):
	"""兼容 MoviePy 新旧版本的淡入效果。"""
	_moviepy = _import_moviepy()
	vfx = _moviepy.vfx
	
	if hasattr(clip, "fx") and hasattr(vfx, "fadein"):
		return clip.fx(vfx.fadein, duration)
	return clip.with_effects([vfx.FadeIn(duration)])


def normalize_time_range(start, end, scene_duration):
	"""
	统一的时间清洗函数，用于处理 visual insert 的 start/end。
	
	规则：
	1. start 和 end 转为 float
	2. start 最小为 0
	3. end 最大不超过 scene_duration
	4. 如果 end <= start，返回 None（表示非法）
	
	参数：
	- start: 开始时间（可为 None、int、float、str）
	- end: 结束时间（可为 None、int、float、str）
	- scene_duration: scene 总时长
	
	返回：
	- (start_clean, end_clean) 元组，或 None 表示非法
	"""
	# 尝试转换为 float
	try:
		start_float = float(start) if start is not None else 0.0
		end_float = float(end) if end is not None else scene_duration
	except (ValueError, TypeError):
		return None
	
	# 边界处理
	start_float = max(0.0, start_float)
	end_float = min(scene_duration, end_float)
	
	# 有效性检查
	if end_float <= start_float:
		return None
	
	return (start_float, end_float)


def get_template_fallback_insert_position(scene, runtime_config=None):
	"""
	从模板中读取 scene 的默认插入位置。
	
	仅在以下条件全部满足时进行读取：
	1. runtime_config.template.template_enabled = True
	2. scene 有 template_role 字段且非空
	3. runtime_config.template.template_name 存在
	4. template_role 在该模板中有效
	
	参数：
	- scene: scene dict
	- runtime_config: RuntimeConfig
	
	返回：
	- str（位置名："top", "center", "bottom"）或 None
	"""
	# 检查模板系统是否启用
	if not runtime_config or not getattr(runtime_config, "template", None):
		return None
	
	if not runtime_config.template.template_enabled:
		return None
	
	template_name = runtime_config.template.template_name
	if not template_name:
		return None
	
	# 检查 scene 是否有 template_role
	if not isinstance(scene, dict):
		return None
	
	template_role = str(scene.get("template_role", "")).strip().lower()
	if not template_role:
		return None
	
	# 校验 template_role（打印 warning 但不报错）
	if not validate_template_role(template_name, template_role, warn=True):
		return None
	
	# 从模板获取默认值
	try:
		role_defaults = get_template_role_defaults(template_name, template_role)
		position = role_defaults.get("default_insert_position")
		if position:
			return str(position).strip().lower()
	except Exception:
		return None
	
	return None


def get_template_fallback_insert_scale(scene, runtime_config=None):
	"""
	尝试从模板中获取默认缩放。
	
	参数：
	- scene: scene dict
	- runtime_config: RuntimeConfig（完整配置）
	
	返回：
	- float 或 None
	"""
	if not isinstance(scene, dict):
		return None
	
	template_role = str(scene.get("template_role", "")).strip().lower()
	if not template_role:
		return None
	
	template_name = getattr(runtime_config, "template_name", None)
	if not template_name:
		return None
	
	try:
		role_defaults = get_template_role_defaults(template_name, template_role)
		scale = role_defaults.get("default_insert_scale")
		if scale:
			return float(scale)
	except Exception:
		pass
	
	return None


def normalize_visual_inserts(scene, scene_duration, runtime_config, video_height):
	"""
	清洗 scene 中的 visual_inserts 字段，返回合法 insert 列表。
	
	参数：
	- scene: 单个 scene dict
	- scene_duration: 该 scene 的总时长
	- runtime_config: VisualInsertConfig 对象
	- video_height: 视频高度（用于位置计算的安全区保护）
	
	返回：
	- 清洗后的 insert 列表，每个 insert 都是合法的 dict
	"""
	if not isinstance(scene, dict):
		return []
	
	visual_inserts = scene.get("visual_inserts")
	if not visual_inserts or not isinstance(visual_inserts, list):
		return []
	
	cleaned_inserts = []
	for idx, insert in enumerate(visual_inserts):
		if not isinstance(insert, dict):
			print(f"[visual_insert_engine] scene visual_inserts[{idx}] 不是 dict 格式，已跳过")
			continue
		
		# 检查必要字段
		insert_type = str(insert.get("type", "")).strip().lower()
		if not insert_type:
			print(f"[visual_insert_engine] scene visual_inserts[{idx}] 缺少 type 字段，已跳过")
			continue
		
		# 第一版只支持 image
		if insert_type != "image":
			print(f"[visual_insert_engine] scene visual_inserts[{idx}] 类型不支持（{insert_type}），已跳过")
			continue
		
		path_value = insert.get("path")
		if not path_value:
			print(f"[visual_insert_engine] scene visual_inserts[{idx}] 缺少 path 字段，已跳过")
			continue
		
		# 统一时间清洗（使用 normalize_time_range）
		time_result = normalize_time_range(
			insert.get("start"),
			insert.get("end"),
			scene_duration
		)
		if time_result is None:
			print(f"[visual_insert_engine] scene visual_inserts[{idx}] start/end 时间非法或逆序，已跳过")
			continue
		
		start_time, end_time = time_result
		
		# 标准化 position 和 scale
		position = normalize_insert_position(insert.get("position"), runtime_config, video_height)
		scale = normalize_insert_scale(insert.get("scale"), runtime_config)
		
		# 构建清洗后的 insert dict
		cleaned_insert = {
			"type": "image",
			"path": str(path_value).strip(),
			"start": start_time,
			"end": end_time,
			"position": position,
			"scale": scale,
		}
		
		cleaned_inserts.append(cleaned_insert)
	
	return cleaned_inserts


def normalize_insert_position(position_value, runtime_config, video_height):
	"""
	标准化 position 值，并计算实际的位置坐标。
	
	设计说明：
	- 为了避免 visual insert 压住底部 UI 卡片，
	  我们限制了 center 和 bottom 的实际显示Y坐标
	- UI 卡片从约 66% 高度处开始，所以 visual insert 最好不超过 55% 高度底部
	
	允许值：
	- "top": Y = 高度的 15%（原有位置）
	- "center": Y = 高度的 35%（调低避开卡片）
	- "bottom": Y = 高度的 55%（留足空间给 UI 卡片）
	
	参数：
	- position_value: 输入的 position 值
	- runtime_config: VisualInsertConfig 对象
	- video_height: 视频高度
	
	返回：
	- ("center", y_coord) 元组，表示在 MoviePy 中的位置
	"""
	if position_value is None:
		position_value = runtime_config.visual_insert.visual_insert_default_position
	
	position_str = str(position_value).strip().lower()
	
	# UI 安全区保护
	if position_str == "top":
		# 上部区域，不遮挡 UI
		y_coord = int(video_height * 0.15)
	elif position_str == "bottom":
		# 底部区域，但要留足空间给卡片（卡片从 66% 开始）
		y_coord = int(video_height * 0.55)
	elif position_str == "center":
		# 中部区域，向上调整避开卡片
		y_coord = int(video_height * 0.35)
	else:
		# 非法值，回退到默认
		print(f"[visual_insert_engine] position 值非法（{position_str}），已回退到默认值")
		position_str = runtime_config.visual_insert.visual_insert_default_position
		if position_str == "top":
			y_coord = int(video_height * 0.15)
		elif position_str == "bottom":
			y_coord = int(video_height * 0.55)
		else:
			y_coord = int(video_height * 0.35)
	
	return ("center", y_coord)


def normalize_insert_scale(scale_value, runtime_config):
	"""
	标准化 scale 值。
	
	允许范围：0.4 ~ 1.0
	默认值：visual_insert_default_scale
	"""
	if scale_value is None:
		return runtime_config.visual_insert.visual_insert_default_scale
	
	try:
		scale_float = float(scale_value)
	except (ValueError, TypeError):
		print(f"[visual_insert_engine] scale 值非法（{scale_value}），已回退到默认值")
		return runtime_config.visual_insert.visual_insert_default_scale
	
	# 允许范围：0.4 ~ 1.0
	if 0.4 <= scale_float <= 1.0:
		return scale_float
	
	print(f"[visual_insert_engine] scale 值超出允许范围（{scale_float}），已回退到默认值")
	return runtime_config.visual_insert.visual_insert_default_scale


def resolve_insert_path(path_value):
	"""
	将相对路径转为项目绝对路径，并检查文件是否存在。
	
	参数：
	- path_value: 路径字符串（可相对或绝对）
	
	返回：
	- (resolved_path: Path, exists: bool)
	"""
	if not path_value:
		return None, False
	
	path_obj = Path(path_value)
	
	# 如果已是绝对路径，直接使用
	if path_obj.is_absolute():
		return path_obj, path_obj.exists()
	
	# 相对路径：相对于项目根目录
	project_root = Path(__file__).resolve().parent.parent
	resolved_path = project_root / path_obj
	
	return resolved_path, resolved_path.exists()


def build_image_insert_clip(insert_item, width, height, runtime_config):
	"""
	为单个 image insert 构建 clip。
	
	重点保证：
	1. 宽高比保持不变（通过 resize/resized 的宽度参数）
	2. 位置避开 UI 卡片区域
	3. fade_in 时长从 config 读取
	4. clip 所有参数正确，无变形
	
	参数：
	- insert_item: 清洗后的 insert dict
	- width: 视频宽度
	- height: 视频高度
	- runtime_config: VisualInsertConfig 对象
	
	返回：
	- ImageClip (已设置 position / scale / duration / fade_in)
	- 若路径非法或文件不存在，返回 None
	"""
	_moviepy = _import_moviepy()
	ImageClip = _moviepy.ImageClip
	
	path_value = insert_item.get("path")
	resolved_path, path_exists = resolve_insert_path(path_value)
	
	if not path_exists:
		print(f"[visual_insert_engine] 图片文件不存在或无法访问: {path_value}")
		return None
	
	try:
		# 生成 ImageClip
		image_clip = ImageClip(str(resolved_path))
	except Exception as e:
		print(f"[visual_insert_engine] 无法加载图片: {resolved_path}，错误: {e}")
		return None
	
	# 提取参数
	start_time = insert_item.get("start", 0.0)
	end_time = insert_item.get("end", 1.0)
	scale = insert_item.get("scale", runtime_config.visual_insert.visual_insert_default_scale)
	position = insert_item.get("position", ("center", int(height * 0.35)))
	
	duration = end_time - start_time
	
	# 1. 设置持续时间
	image_clip = _set_duration(image_clip, duration)
	
	# 2. 缩放处理
	# 关键：按 scale 比例缩放，保持宽高比
	# scale 的定义：相对视频宽度的比例
	# 例如 scale=0.72 表示图片最终宽度 = video_width * 0.72
	try:
		img_width = image_clip.w
		img_height = image_clip.h
	except Exception as e:
		print(f"[visual_insert_engine] 无法获取图片尺寸: {resolved_path}，错误: {e}")
		return None
	
	if img_width <= 0 or img_height <= 0:
		print(f"[visual_insert_engine] 图片尺寸非法: {resolved_path}")
		return None
	
	# 计算目标宽度和高度（保持宽高比）
	target_width = int(width * scale)
	# 高度根据宽高比自动计算，保持原始比例
	target_height = int(target_width * img_height / img_width)
	
	try:
		# 使用 resize 或 resized 方法，两者都会保持宽高比
		if hasattr(image_clip, "resize"):
			# 旧 MoviePy API
			image_clip = image_clip.resize(width=target_width)
		elif hasattr(image_clip, "resized"):
			# 新 MoviePy 2.2.1+ API
			image_clip = image_clip.resized(width=target_width)
		else:
			# 无法缩放，但继续尝试用原尺寸
			print(f"[visual_insert_engine] 无法使用标准缩放方法，将使用原尺寸")
	except Exception as e:
		print(f"[visual_insert_engine] 图片缩放失败: {resolved_path}，错误: {e}")
		# 继续使用未缩放的 clip
	
	# 3. 位置处理
	# position 已经在 normalize_insert_position 中计算为 ("center", y) 元组
	image_clip = _set_position(image_clip, position)
	
	# 4. 应用淡入效果
	# 关键：fade 时长从 config 读取，不硬编码
	fade_duration = runtime_config.visual_insert.visual_insert_default_fade_duration
	if fade_duration > 0:
		try:
			image_clip = _apply_fadein(image_clip, fade_duration)
		except Exception as e:
			print(f"[visual_insert_engine] 淡入效果应用失败: {e}，继续使用无淡入")
	
	# 5. 设置开始时间（相对于 scene 起点）
	if start_time > 0:
		try:
			if hasattr(image_clip, "set_start"):
				image_clip = image_clip.set_start(start_time)
			elif hasattr(image_clip, "with_start"):
				image_clip = image_clip.with_start(start_time)
		except Exception as e:
			print(f"[visual_insert_engine] 设置开始时间失败: {e}，继续不设置 start")
	
	return image_clip


def build_visual_insert_clips(scene, scene_duration, width, height, runtime_config):
	"""
	为单个 scene 构建所有视觉插入 clip 列表。
	
	关键点：
	1. visual_insert_enabled 开关检查是真实有效的
	2. 返回的所有 clip 都已正确配置
	3. 所有 clip 都会在 video_builder 中进行 register_clip
	
	参数：
	- scene: 单个 scene dict
	- scene_duration: 该 scene 的总时长
	- width: 视频宽度
	- height: 视频高度
	- runtime_config: VisualInsertConfig 对象
	
	返回：
	- 合法 insert clip 列表（若无 visual_inserts 或开关关闭，返回空列表）
	"""
	# 关键检查：visual_insert_enabled 开关
	if not runtime_config.visual_insert.visual_insert_enabled:
		# 开关关闭时，直接跳过所有逻辑，即使 scene 中有 visual_inserts 也不处理
		return []
	
	# 清洗 visual_inserts（已整合时间清洗函数）
	cleaned_inserts = normalize_visual_inserts(scene, scene_duration, runtime_config, height)
	
	if not cleaned_inserts:
		# 无合法 insert，返回空列表
		return []
	
	# 为每个 insert 构建 clip
	insert_clips = []
	for insert_item in cleaned_inserts:
		clip = build_image_insert_clip(insert_item, width, height, runtime_config)
		if clip is not None:
			insert_clips.append(clip)
			print(f"[visual_insert_engine] 已构建图片插入 clip: {insert_item['path']} ({insert_item['start']:.2f}s - {insert_item['end']:.2f}s)")
	
	return insert_clips
