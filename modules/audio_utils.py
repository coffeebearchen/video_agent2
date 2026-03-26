# -*- coding: utf-8 -*-
"""
音频工具模块 (audio_utils.py)

职责：
1. 读取音频文件时长
2. 支持 wav 格式（第一版）
3. 提供统一接口

【设计说明】
- 使用标准库，不引入重依赖
- 第一版仅支持 wav
- 对无效文件返回 0.0
"""

import struct
import os
from pathlib import Path


def get_wav_duration(file_path: str) -> float:
	"""
	读取 WAV 音频文件的时长。
	
	参数：
	- file_path: wav 文件路径（可相对或绝对）
	
	返回：
	- float: 音频时长（秒）。若文件无效或不存在，返回 0.0
	
	实现原理：
	- 解析 WAV 文件头的 RIFF / fmt / data 块
	- 根据采样率与采样宽度计算时长
	- 异常时返回 0.0，不抛错
	"""
	if not file_path:
		return 0.0
	
	try:
		# 转为绝对路径
		path_obj = Path(file_path)
		if not path_obj.is_absolute():
			# 相对于项目根目录
			project_root = Path(__file__).resolve().parent.parent
			path_obj = project_root / path_obj
		
		# 检查文件是否存在
		if not path_obj.exists():
			return 0.0
		
		# 打开文件并读取 WAV 头
		with open(path_obj, "rb") as f:
			# 读取 RIFF 头
			riff_marker = f.read(4)
			if riff_marker != b"RIFF":
				return 0.0
			
			# 跳过 file_size（4 字节）
			f.read(4)
			
			# 检查 WAVE 标记
			wave_marker = f.read(4)
			if wave_marker != b"WAVE":
				return 0.0
			
			# 查找 fmt 块
			num_channels = 0
			sample_rate = 0
			bits_per_sample = 0
			
			while True:
				chunk_header = f.read(8)
				if len(chunk_header) < 8:
					break
				
				chunk_id = chunk_header[:4]
				chunk_size = struct.unpack("<I", chunk_header[4:8])[0]
				
				if chunk_id == b"fmt ":
					# 解析 fmt 块
					fmt_data = f.read(chunk_size)
					if len(fmt_data) >= 14:
						num_channels = struct.unpack("<H", fmt_data[2:4])[0]
						sample_rate = struct.unpack("<I", fmt_data[4:8])[0]
						bits_per_sample = struct.unpack("<H", fmt_data[14:16])[0]
					break
				elif chunk_id == b"data":
					# 暂时跳过，稍后处理
					f.seek(chunk_size, 1)
				else:
					# 跳过其他块
					f.seek(chunk_size, 1)
			
			# 重新打开文件，查找 data 块
			f.seek(0)
			riff_marker = f.read(4)
			f.read(4)
			wave_marker = f.read(4)
			
			data_size = 0
			while True:
				chunk_header = f.read(8)
				if len(chunk_header) < 8:
					break
				
				chunk_id = chunk_header[:4]
				chunk_size = struct.unpack("<I", chunk_header[4:8])[0]
				
				if chunk_id == b"data":
					data_size = chunk_size
					break
				else:
					f.seek(chunk_size, 1)
			
			# 计算时长
			if sample_rate > 0 and data_size > 0:
				# 每个样本占用的字节数
				bytes_per_sample = (bits_per_sample // 8) * num_channels
				if bytes_per_sample > 0:
					num_samples = data_size // bytes_per_sample
					duration = num_samples / sample_rate
					return round(duration, 3)
			
			return 0.0
	
	except Exception:
		# 异常时返回 0.0，不抛错
		return 0.0


def get_audio_duration(file_path: str) -> float:
	"""
	读取音频文件时长（统一接口）。
	
	参数：
	- file_path: 音频文件路径
	
	返回：
	- float: 音频时长（秒）
	
	【设计说明】
	- 第一版仅支持 wav
	- 后续可扩展支持其他格式
	"""
	if not file_path:
		return 0.0
	
	file_path_str = str(file_path).strip().lower()
	
	# 检查文件扩展名
	if file_path_str.endswith(".wav"):
		return get_wav_duration(file_path)
	
	# 暂不支持其他格式，返回 0.0
	return 0.0
