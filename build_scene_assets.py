# -*- coding: utf-8 -*-
"""
build_scene_assets.py

【场景素材自动生成模块】

目的：
当当前场景素材输出缺失或无效时，
从当前 scene_plan 自动生成最小可用版本。

运行方式（独立）：
    python build_scene_assets.py

或在其他模块中调用：
    from build_scene_assets import build_scene_assets
    build_scene_assets()

【video_engine.py 兼容性设计】
本模块生成的 scene_assets.json 完全对标 video_engine.py 的真实读取逻辑。

video_engine 读取的字段：
  - type: 资产类型（image/video/text_card）- 必需
  - file: 资产文件路径 - 可选
  - scene_id, section, asset_id, duration: 日志和计算用

video_engine 不读取的字段：
  - audio_file: 音频来自 script.json 或 audio/ 目录，不从 scene_assets 读
  - start, match_score, is_fallback, tags, text: 不使用

策略：
- 结构化、可验证、最小可用
- 不做智能素材推荐，不做标签系统
- video_engine 自动 fallback 到平面卡图
"""

from __future__ import annotations

import json
from typing import Any, Dict, List

from asset_selector import select_asset_for_text
from modules import project_paths


PROJECT_ROOT = getattr(
    project_paths,
    "PROJECT_ROOT",
    project_paths.get_project_root(),
)
DATA_CURRENT_DIR = getattr(
    project_paths,
    "DATA_CURRENT_DIR",
    project_paths.get_data_current_dir(),
)
SCENE_PLAN_FILE = getattr(
    project_paths,
    "CURRENT_SCENE_PLAN_JSON_PATH",
    project_paths.get_data_current_dir() / "scene_plan.json",
)
SCENE_ASSETS_FILE = getattr(
    project_paths,
    "SCENE_ASSETS_JSON_PATH",
    project_paths.get_data_current_dir() / "scene_assets.json",
)
SCRIPT_FILE = getattr(
    project_paths,
    "SCRIPT_JSON_PATH",
    project_paths.get_project_root() / "script.json",
)

REQUIRED_SELECTOR_KEYS = {
    "matched",
    "asset_type",
    "asset_file",
    "keyword",
}


def load_scene_plan() -> Dict[str, Any]:
    """读取 scene_plan.json。"""
    print(f"[BUILD_ASSETS] 读取 scene_plan 路径：{SCENE_PLAN_FILE}")
    if not SCENE_PLAN_FILE.exists():
        raise FileNotFoundError(f"[BUILD_ASSETS] scene_plan.json 不存在：{SCENE_PLAN_FILE}")

    with open(SCENE_PLAN_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    return data


def validate_existing_scene_assets() -> bool:
    """
    验证现有 scene_assets.json 的有效性。

    校验标准与 validate_scene_assets_strict() 一致：
    - type: 必需（video_engine 核心字段）
    - duration: 必需（video_engine 计算字段）
    - file: 可选（允许为空，触发 fallback）

    返回：
        True 如果文件存在且有效，False 否则
    """
    if not SCENE_ASSETS_FILE.exists():
        return False

    try:
        with open(SCENE_ASSETS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            assets = data
        elif isinstance(data, dict) and "scene_assets" in data:
            assets = data.get("scene_assets", [])
        else:
            return False

        if not assets:
            return False

        required_fields = ["type", "duration"]
        for asset in assets:
            for field in required_fields:
                if field not in asset:
                    return False

        return True

    except Exception:
        return False


def normalize_asset_match_result(scene_id: Any, text: str) -> Dict[str, Any]:
    """调用 asset_selector，并对返回结构做最小校验。"""
    try:
        asset_match_result = select_asset_for_text(text)
    except Exception as error:
        print(f"[BUILD_ASSETS][WARN] Scene {scene_id} 素材选择异常：{error}")
        return {
            "matched": False,
            "asset_type": "text_card",
            "asset_file": "",
            "keyword": "",
        }

    if not isinstance(asset_match_result, dict):
        print(
            f"[BUILD_ASSETS][WARN] Scene {scene_id} 素材选择返回结构异常："
            f"{type(asset_match_result).__name__}"
        )
        return {
            "matched": False,
            "asset_type": "text_card",
            "asset_file": "",
            "keyword": "",
        }

    missing_keys = sorted(REQUIRED_SELECTOR_KEYS - set(asset_match_result.keys()))
    if missing_keys:
        print(
            f"[BUILD_ASSETS][WARN] Scene {scene_id} 素材选择缺少字段："
            f"{', '.join(missing_keys)}"
        )
        return {
            "matched": False,
            "asset_type": "text_card",
            "asset_file": "",
            "keyword": "",
        }

    return asset_match_result


def build_minimal_scene_assets(scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    从 scene_plan 构建最小可用的 scene_assets。

    【TASK 6B 集成】
    现在会调用 asset_selector.select_asset_for_text() 自动匹配素材：
    - 如果匹配到，使用匹配的 asset_file 和 asset_type（通常是 image）
    - 如果无匹配，fallback 到原有的 text_card（让 video_engine 继续 fallback）

    【video_engine.py 真实消费的字段】
    video_engine.build_scene_visual_clip() 读取以下字段：
    - type: 资产类型（image/video/text_card）- 必需，控制处理流程
    - file: 资产文件路径 - 可选，为空时触发渲染层 fallback
    - scene_id: 场景 ID - 可选，用于日志
    - section: 分类标签 - 可选，用于日志
    - asset_id: 资产标识 - 可选，用于日志
    - duration: 场景时长 - 可选，默认为 DEFAULT_CARD_DURATION

    【video_engine.py 不读取的字段】（虽然旧格式有）
    - audio_file: video_engine 从 script.json 和 audio/ 目录动态获取，不从 scene_assets 读
    - start: 不使用
    - match_score: 不使用
    - is_fallback: 不使用
    - tags: 不使用
    - text: 不使用

    参数：
        scenes: scene_plan.json 中的 scenes 列表

    返回：
        scene_assets 列表，每条记录包含最小必需字段
    """
    print("[BUILD_ASSETS] 开始构建场景素材")
    scene_assets = []

    for index, scene in enumerate(scenes):
        scene_id = scene.get("scene_id", index + 1)
        text = scene.get("text", "")
        duration = scene.get("duration", 7.0)
        section = scene.get("section", "explain")

        asset_match_result = normalize_asset_match_result(scene_id, text)

        if asset_match_result["matched"]:
            asset_type = asset_match_result["asset_type"]
            asset_file = asset_match_result["asset_file"]
            match_keyword = asset_match_result["keyword"]
            match_score = asset_match_result.get("match_score", 0)
            is_fallback = asset_match_result.get("is_fallback", False)
            matched_keyword = asset_match_result.get("matched_keyword", match_keyword)
            print(
                f"[BUILD_ASSETS] Scene {scene_id} 使用素材："
                f"type={asset_type} | file={asset_file} | score={match_score}"
            )
        else:
            asset_type = "text_card"
            asset_file = ""
            match_keyword = asset_match_result["keyword"]
            match_score = asset_match_result.get("match_score", 0)
            is_fallback = asset_match_result.get("is_fallback", True)
            matched_keyword = asset_match_result.get("matched_keyword", "")
            print(f"[BUILD_ASSETS] Scene {scene_id} fallback：text_card | score={match_score}")

        asset_record = {
            "type": asset_type,
            "file": asset_file,
            "scene_id": scene_id,
            "section": section,
            "asset_id": f"auto_scene_{scene_id}",
            "duration": float(duration),
            "asset_type": asset_type,
            "asset_file": asset_file,
            "text": text,
            "start": None,
            "match_score": match_score,
            "is_fallback": is_fallback,
            "matched_keyword": matched_keyword,
        }

        scene_assets.append(asset_record)

    return scene_assets


def write_scene_assets(scene_assets: List[Dict[str, Any]]) -> None:
    """写入 scene_assets.json。"""
    output = {
        "scene_assets": scene_assets,
    }

    print(f"[BUILD_ASSETS] 输出 scene_assets 路径：{SCENE_ASSETS_FILE}")
    if not DATA_CURRENT_DIR.exists():
        DATA_CURRENT_DIR.mkdir(parents=True, exist_ok=True)

    with open(SCENE_ASSETS_FILE, "w", encoding="utf-8") as file:
        json.dump(output, file, indent=2, ensure_ascii=False)

    print(f"[BUILD_ASSETS] 已写出 scene_assets.json：{SCENE_ASSETS_FILE}")


def build_scene_assets() -> None:
    """
    主入口：构建并保存 scene_assets.json。

    逻辑：
    1. 如果 scene_assets.json 不存在或无效，就重新生成
    2. 如果存在且有效，跳过生成
    """
    print("\n" + "=" * 60)
    print("📦 场景素材自动生成模块")
    print("=" * 60 + "\n")

    try:
        print(f"[BUILD_ASSETS] 项目根路径：{PROJECT_ROOT}")
        print(f"[BUILD_ASSETS] 读取 scene_plan 路径：{SCENE_PLAN_FILE}")
        print(f"[BUILD_ASSETS] 读取 script 路径：{SCRIPT_FILE}")
        print(f"[BUILD_ASSETS] 输出 scene_assets 路径：{SCENE_ASSETS_FILE}")

        if not SCRIPT_FILE.exists():
            print(f"[BUILD_ASSETS][WARN] script.json 不存在：{SCRIPT_FILE}")

        if SCENE_ASSETS_FILE.exists():
            if validate_existing_scene_assets():
                print("[BUILD_ASSETS] scene_assets.json 已存在且有效，跳过生成")
                print(f"[BUILD_ASSETS] 当前有效文件：{SCENE_ASSETS_FILE}")
                return

            print("[BUILD_ASSETS] scene_assets.json 存在但无效，将重新生成")

        print("[BUILD_ASSETS] 开始读取 scene_plan")
        plan = load_scene_plan()

        scenes = plan.get("scenes", [])
        if not scenes:
            raise ValueError("[BUILD_ASSETS] scene_plan.json 中未找到 scenes")

        print(f"[BUILD_ASSETS] 场景总数：{len(scenes)}")
        scene_assets = build_minimal_scene_assets(scenes)

        write_scene_assets(scene_assets)

        matched_count = sum(1 for asset in scene_assets if not asset["is_fallback"])
        fallback_count = len(scene_assets) - matched_count

        print("\n✅ 完成！scene_assets.json 已准备就绪")
        print(f"   - 场景数：{len(scene_assets)}")
        print(f"   - 素材匹配数（TASK 6B）：{matched_count}")
        print(f"   - Fallback 数（text_card）：{fallback_count}")
        print("   - 素材文件：由 asset_selector 或 fallback 决定")
        print("   - 音频：由 video_engine 从 script.json 或 audio/ 目录动态获取\n")

    except Exception as error:
        print(f"\n[BUILD_ASSETS][ERROR] 生成失败：{error}")
        raise


def validate_scene_assets_strict() -> bool:
    """
    严格验证 scene_assets.json 结构与字段。

    检查项：
    - 文件存在
    - 格式有效（支持两种顶层结构）
    - 包含 video_engine 真实需要的字段
    - 字段类型正确

    返回：
        True 如果完全有效，False 如果任何检查失败
    """
    if not SCENE_ASSETS_FILE.exists():
        print("[BUILD_ASSETS][ERROR] scene_assets.json 不存在")
        return False

    try:
        with open(SCENE_ASSETS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, list):
            assets = data
        elif isinstance(data, dict) and "scene_assets" in data:
            assets = data.get("scene_assets", [])
        else:
            print("[BUILD_ASSETS][ERROR] scene_assets.json 格式错误，应为 list 或 {'scene_assets': [...]} ")
            return False

        if not assets:
            print("[BUILD_ASSETS][ERROR] scene_assets.json 为空")
            return False

        required_fields = ["type", "duration"]
        video_engine_expected_fields = ["type", "file", "scene_id", "section", "asset_id", "duration"]

        for index, asset in enumerate(assets):
            for field in required_fields:
                if field not in asset:
                    print(f"[BUILD_ASSETS][ERROR] scene_assets[{index}] 缺少必需字段 '{field}'")
                    return False

            if not isinstance(asset.get("duration"), (int, float)):
                print(f"[BUILD_ASSETS][ERROR] scene_assets[{index}].duration 应为 number")
                return False

        print(f"[BUILD_ASSETS] scene_assets.json 有效（{len(assets)} 条记录）")
        print(f"[BUILD_ASSETS] video_engine 期望字段：{', '.join(required_fields)}")
        print(
            "[BUILD_ASSETS] 可选日志/计算字段："
            f"{', '.join(sorted(set(video_engine_expected_fields) - set(required_fields)))}"
        )
        return True

    except json.JSONDecodeError as error:
        print(f"[BUILD_ASSETS][ERROR] JSON 格式错误：{error}")
        return False
    except Exception as error:
        print(f"[BUILD_ASSETS][ERROR] 验证失败：{error}")
        return False


if __name__ == "__main__":
    build_scene_assets()
    validate_scene_assets_strict()
