# -*- coding: utf-8 -*-
"""
用户素材优先解析模块。

职责：
1. 解析 scene 中的 user_anchor
2. 解析 scene 中的 user_local_assets
3. 返回当前 scene 最应该使用的用户素材
"""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def resolve_asset_path(path_value):
	"""
	解析相对路径和绝对路径。
	
	返回：
	- (resolved_path, exists)
	"""
	if not path_value:
		return None, False

	try:
		path_obj = Path(str(path_value).strip())
	except Exception:
		return None, False

	if not path_obj.is_absolute():
		path_obj = PROJECT_ROOT / path_obj

	return path_obj, path_obj.exists()


def normalize_user_asset_item(asset_item):
	"""
	标准化单个用户素材项。
	
	输出统一结构：
	{
		"asset_type": "video" | "image",
		"asset_path": Path对象
	}
	"""
	if not isinstance(asset_item, dict):
		return None

	asset_type = str(asset_item.get("type", "") or "").strip().lower()
	if asset_type not in {"video", "image"}:
		return None

	file_value = asset_item.get("file")
	asset_path, exists = resolve_asset_path(file_value)
	if not exists or asset_path is None:
		return None

	return {
		"asset_type": asset_type,
		"asset_path": asset_path,
	}


def resolve_scene_user_anchor(scene):
	"""
	读取 scene["user_anchor"] 并返回标准化素材。
	"""
	if not isinstance(scene, dict):
		return None

	anchor = scene.get("user_anchor")
	asset_info = normalize_user_asset_item(anchor)
	if asset_info is None:
		return None

	asset_info["asset_source"] = "user_anchor"
	return asset_info


def resolve_scene_user_local_asset(scene):
	"""
	读取 scene["user_local_assets"] 并返回第一个有效素材。
	"""
	if not isinstance(scene, dict):
		return None

	asset_items = scene.get("user_local_assets")
	if not isinstance(asset_items, list):
		return None

	for asset_item in asset_items:
		asset_info = normalize_user_asset_item(asset_item)
		if asset_info is not None:
			asset_info["asset_source"] = "user_local_assets"
			return asset_info

	return None


def resolve_scene_priority_asset(scene):
	"""
	按优先级返回 scene 的用户素材。
	
	优先级：
	- user_anchor
	- user_local_assets
	"""
	anchor_asset = resolve_scene_user_anchor(scene)
	if anchor_asset is not None:
		return anchor_asset

	local_asset = resolve_scene_user_local_asset(scene)
	if local_asset is not None:
		return local_asset

	return None