# -*- coding: utf-8 -*-
"""
user_anchor 轻量设置工具。

作用：
1. 读取 scene_plan.json
2. 让用户通过命令行选择 scene 并填写 user_anchor
3. 将 user_anchor 安全写回 scene_plan.json

运行方式：
    python tools/set_user_anchor.py
"""

import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_CURRENT_DIR = BASE_DIR / "data" / "current"
ROOT_SCENE_PLAN_FILE = BASE_DIR / "scene_plan.json"
DATA_CURRENT_SCENE_PLAN_FILE = DATA_CURRENT_DIR / "scene_plan.json"


def load_scene_plan():
	"""
	读取 scene_plan.json，并返回原始数据、scenes、来源文件和结构类型。
	"""
	input_file = None

	if ROOT_SCENE_PLAN_FILE.exists():
		input_file = ROOT_SCENE_PLAN_FILE
	elif DATA_CURRENT_SCENE_PLAN_FILE.exists():
		input_file = DATA_CURRENT_SCENE_PLAN_FILE
	else:
		raise FileNotFoundError(
			f"scene_plan.json 不存在：{ROOT_SCENE_PLAN_FILE} 或 {DATA_CURRENT_SCENE_PLAN_FILE}"
		)

	with open(input_file, "r", encoding="utf-8") as file:
		raw_data = json.load(file)

	if isinstance(raw_data, dict):
		structure_type = "dict"
		scenes = raw_data.get("scenes", [])
	elif isinstance(raw_data, list):
		structure_type = "list"
		scenes = raw_data
	else:
		raise ValueError("scene_plan.json 结构非法，只支持 dict/scenes 或 list 结构")

	if not isinstance(scenes, list):
		raise ValueError("scene_plan.json 中 scenes 不是合法列表")

	return raw_data, scenes, input_file, structure_type


def show_scene_summary(scenes):
	"""
	打印当前 scenes 的简要信息，便于用户选择场景编号。
	"""
	print("当前可用场景：")
	for index, scene in enumerate(scenes):
		if not isinstance(scene, dict):
			scene = {}

		scene_type = str(scene.get("type", "") or "")
		text = str(scene.get("text", "") or "")
		text_preview = text[:24]
		if len(text) > 24:
			text_preview += "..."

		print(f"[{index}] type={scene_type} | text={text_preview}")


def ask_user_input(scenes):
	"""
	通过命令行读取用户输入，并完成最基本校验。
	"""
	while True:
		raw_scene_index = input("请输入 scene 编号：").strip()
		try:
			scene_index = int(raw_scene_index)
		except ValueError:
			print("输入无效：scene 编号必须是整数，请重新输入。")
			continue

		if scene_index < 0 or scene_index >= len(scenes):
			print("输入无效：scene 编号超出范围，请重新输入。")
			continue
		break

	while True:
		asset_type = str(input("请输入素材类型（image / video）：") or "").strip().lower()
		if asset_type not in {"image", "video"}:
			print("输入无效：素材类型只能是 image 或 video。")
			continue
		break

	while True:
		asset_file = str(input("请输入素材路径：") or "").strip()
		if not asset_file:
			print("输入无效：素材路径不能为空。")
			continue
		break

	role = str(input("请输入 role（可直接回车，默认 main）：") or "").strip()
	if not role:
		role = "main"

	asset_path = Path(asset_file)
	if not asset_path.is_absolute():
		asset_path = BASE_DIR / asset_path

	if not asset_path.exists():
		print("提示：当前路径文件未找到，仍将写入 scene_plan.json，后续运行时会由主链自动回退。")

	return scene_index, asset_type, asset_file, role


def build_user_anchor(asset_type, asset_file, role):
	"""
	生成标准 user_anchor 数据结构。
	"""
	return {
		"type": asset_type,
		"file": asset_file,
		"role": role or "main",
	}


def write_user_anchor_to_scene(raw_data, scenes, structure_type, scene_index, user_anchor):
	"""
	将 user_anchor 写入指定 scene，已存在则直接覆盖。
	"""
	if structure_type == "dict":
		target_scenes = raw_data.get("scenes", [])
	else:
		target_scenes = raw_data

	if not isinstance(target_scenes, list):
		raise ValueError("scene_plan.json 的 scenes 结构非法，无法写入 user_anchor")

	if not isinstance(target_scenes[scene_index], dict):
		target_scenes[scene_index] = {}

	target_scenes[scene_index]["user_anchor"] = user_anchor


def save_scene_plan(raw_data, source_file, structure_type):
	"""
	保存 scene_plan.json，优先保存回根目录；根目录不存在时按来源保存。
	"""
	if ROOT_SCENE_PLAN_FILE.exists() or source_file == ROOT_SCENE_PLAN_FILE:
		target_file = ROOT_SCENE_PLAN_FILE
	else:
		target_file = source_file

	target_file.parent.mkdir(parents=True, exist_ok=True)
	with open(target_file, "w", encoding="utf-8") as file:
		json.dump(raw_data, file, ensure_ascii=False, indent=2)

	return target_file


def main():
	"""
	主流程：读取 scene_plan，展示摘要，接收输入，写回 user_anchor，保存文件。
	"""
	print("----------------------------------------")
	print("user_anchor 轻量设置工具")
	print("作用：为 scene_plan.json 中指定场景写入 user_anchor")
	print("----------------------------------------")

	raw_data, scenes, source_file, structure_type = load_scene_plan()
	print(f"已读取：{source_file}")

	if not scenes:
		print("当前没有可写入的 scene，程序结束。")
		return

	show_scene_summary(scenes)
	scene_index, asset_type, asset_file, role = ask_user_input(scenes)
	user_anchor = build_user_anchor(asset_type, asset_file, role)

	write_user_anchor_to_scene(raw_data, scenes, structure_type, scene_index, user_anchor)
	saved_file = save_scene_plan(raw_data, source_file, structure_type)

	print()
	print(f"已成功写入 scene {scene_index} 的 user_anchor")
	print(f"类型：{user_anchor['type']}")
	print(f"路径：{user_anchor['file']}")
	print(f"角色：{user_anchor['role']}")
	print(f"保存文件：{saved_file}")
	print()
	print("建议下一步执行：")
	print("1. python plan_compiler.py")
	print("2. python video_builder.py")


if __name__ == "__main__":
	main()