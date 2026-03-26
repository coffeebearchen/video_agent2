# -*- coding: utf-8 -*-
"""
build_scene_assets.py

【场景素材自动生成模块】

目的：
当 data/current/scene_assets.json 缺失或无效时，
从 scene_plan.json 自动生成最小可用版本

运行方式（独立）：
    python build_scene_assets.py

或在其他模块中调用：
    from build_scene_assets import build_scene_assets
    build_scene_assets()

输入：
    data/current/scene_plan.json

输出：
    data/current/scene_assets.json

【video_engine.py 兼容性设计】
本模块生成的 scene_assets.json 完全对标 video_engine.py 的真实读取逻辑：

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
- video_engine 自动 fallback 到 images/flat/card_x.png
"""

import json
from pathlib import Path
from typing import Any, Dict, List


BASE_DIR = Path(__file__).resolve().parent
DATA_CURRENT_DIR = BASE_DIR / "data" / "current"

SCENE_PLAN_FILE = DATA_CURRENT_DIR / "scene_plan.json"
SCENE_ASSETS_FILE = DATA_CURRENT_DIR / "scene_assets.json"


def load_scene_plan() -> Dict[str, Any]:
    """读取 scene_plan.json"""
    if not SCENE_PLAN_FILE.exists():
        raise FileNotFoundError(f"❌ scene_plan.json 不存在：{SCENE_PLAN_FILE}")
    
    with open(SCENE_PLAN_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    return data


def validate_existing_scene_assets() -> bool:
    """
    验证现有 scene_assets.json 的有效性
    
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
        with open(SCENE_ASSETS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 支持两种格式
        if isinstance(data, list):
            assets = data
        elif isinstance(data, dict) and "scene_assets" in data:
            assets = data.get("scene_assets", [])
        else:
            return False
        
        # 检查最小有效性
        if not assets:
            return False
        
        # 【关键】检查 video_engine 真实需要的字段，与 validate_scene_assets_strict() 保持一致
        required_fields = ["type", "duration"]  # video_engine 核心字段
        for asset in assets:
            for field in required_fields:
                if field not in asset:
                    return False
        
        return True
        
    except Exception:
        return False


def build_minimal_scene_assets(scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    从 scene_plan 构建最小可用的 scene_assets
    
    【video_engine.py 真实消费的字段】
    video_engine.build_scene_visual_clip() 读取以下字段：
    - type: 资产类型（image/video/text_card）- 必需，控制处理流程
    - file: 资产文件路径 - 可选，为空时 fallback 到 images/flat/card_x.png
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
    scene_assets = []
    
    for idx, scene in enumerate(scenes):
        scene_id = scene.get("scene_id", idx + 1)
        text = scene.get("text", "")
        duration = scene.get("duration", 7.0)
        
        # 优先从 scene_plan.json 读取 section，否则使用默认值
        section = scene.get("section", "explain")
        
        # 构建最小 scene_asset 记录
        # 【关键】：type 和 file 是 video_engine 真实读取的字段名
        asset_record = {
            # 【video_engine 必需字段】
            "type": "text_card",          # ← video_engine 读取 scene.get("type")
            "file": "",                   # ← video_engine 读取 scene.get("file")，空文件让它 fallback
            
            # 【video_engine 可选但会打印的字段】
            "scene_id": scene_id,
            "section": section,
            "asset_id": f"fallback_scene_{scene_id}",
            "duration": float(duration),
            
            # 【支持向前兼容的别名字段】（某些工具可能期望这些名字）
            "asset_type": "text_card",
            "asset_file": "",
            
            # 【元数据字段】（不影响 video_engine，可保留或删除）
            "text": text,
            "start": None,
            "match_score": 0,
            "is_fallback": True
        }
        
        scene_assets.append(asset_record)
    
    return scene_assets


def write_scene_assets(scene_assets: List[Dict[str, Any]]) -> None:
    """写入 scene_assets.json"""
    output = {
        "scene_assets": scene_assets
    }
    
    # 确保输出目录存在
    DATA_CURRENT_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(SCENE_ASSETS_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"✅ 已生成 scene_assets.json：{SCENE_ASSETS_FILE}")


def build_scene_assets() -> None:
    """
    主入口：构建并保存 scene_assets.json
    
    逻辑：
    1. 如果 scene_assets.json 不存在或无效，就重新生成
    2. 如果存在且有效，跳过生成
    """
    print("\n" + "=" * 60)
    print("📦 场景素材自动生成模块")
    print("=" * 60 + "\n")
    
    try:
        # 检查现有 scene_assets.json 的有效性
        if SCENE_ASSETS_FILE.exists():
            if validate_existing_scene_assets():
                print(f"✅ scene_assets.json 已存在且有效，跳过生成")
                print(f"   路径：{SCENE_ASSETS_FILE}")
                return
            else:
                print(f"⚠️  scene_assets.json 存在但无效，将重新生成")
        
        # 读取 scene_plan.json
        print(f"📖 读取 scene_plan.json...")
        plan = load_scene_plan()
        
        scenes = plan.get("scenes", [])
        if not scenes:
            raise ValueError("❌ scene_plan.json 中未找到 scenes")
        
        print(f"   场景总数：{len(scenes)}")
        
        # 生成最小可用的 scene_assets
        print(f"\n🔨 生成最小可用 scene_assets...")
        scene_assets = build_minimal_scene_assets(scenes)
        
        # 保存到文件
        print(f"\n💾 保存到文件...")
        write_scene_assets(scene_assets)
        
        print(f"\n✅ 完成！scene_assets.json 已准备就绪")
        print(f"   - 场景数：{len(scene_assets)}")
        print(f"   - 默认素材类型：text_card")
        print(f"   - 素材文件：空（让 video_engine fallback 到 images/flat/card_x.png）")
        print(f"   - 音频：由 video_engine 从 script.json 或 audio/ 目录动态获取\n")
        
    except Exception as e:
        print(f"\n❌ 生成失败：{str(e)}")
        raise


def validate_scene_assets_strict() -> bool:
    """
    严格验证 scene_assets.json 结构与字段
    
    检查项：
    - 文件存在
    - 格式有效（支持两种顶层结构）
    - 包含 video_engine 真实需要的字段
    - 字段类型正确
    
    返回：
        True 如果完全有效，False 如果任何检查失败
    """
    if not SCENE_ASSETS_FILE.exists():
        print(f"❌ scene_assets.json 不存在")
        return False
    
    try:
        with open(SCENE_ASSETS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # 支持两种格式
        if isinstance(data, list):
            assets = data
        elif isinstance(data, dict) and "scene_assets" in data:
            assets = data.get("scene_assets", [])
        else:
            print(f"❌ scene_assets.json 格式错误，应为 list 或 {{'scene_assets': [...]}}")
            return False
        
        if not assets:
            print(f"❌ scene_assets.json 为空")
            return False
        
        # 【关键】检查 video_engine 真实读取的字段
        # video_engine 在 build_scene_visual_clip() 中直接使用：
        # - scene.get("type")
        # - scene.get("file")
        # - scene.get("scene_id")
        # - scene.get("section")
        # - scene.get("asset_id")
        # - scene.get("duration")
        
        required_fields = ["type", "duration"]  # video_engine 最关键的两个字段
        video_engine_expected_fields = ["type", "file", "scene_id", "section", "asset_id", "duration"]
        
        for idx, asset in enumerate(assets):
            # 必需字段检查
            for field in required_fields:
                if field not in asset:
                    print(f"❌ scene_assets[{idx}] 缺少必需字段 '{field}'")
                    return False
            
            # 字段类型检查
            if not isinstance(asset.get("duration"), (int, float)):
                print(f"❌ scene_assets[{idx}].duration 应为 number")
                return False
        
        print(f"✅ scene_assets.json 有效（{len(assets)} 条记录）")
        print(f"   video_engine 期望的字段：{', '.join(required_fields)}")
        print(f"   （可选字段用于日志/计算：{', '.join(set(video_engine_expected_fields) - set(required_fields))}）")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON 格式错误：{str(e)}")
        return False
    except Exception as e:
        print(f"❌ 验证失败：{str(e)}")
        return False


if __name__ == "__main__":
    build_scene_assets()
    validate_scene_assets_strict()
