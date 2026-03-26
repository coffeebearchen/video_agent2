# -*- coding: utf-8 -*-
"""
tools/run_build_scene_assets.py

作用：
独立运行 build_scene_assets.py
用于验证 scene_assets.json 是否正确生成
"""

import json
from pathlib import Path
import sys

# ====== 路径定义（严格使用 current） ======
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "current"

SCENE_PLAN_PATH = DATA_DIR / "scene_plan.json"
SCENE_ASSETS_PATH = DATA_DIR / "scene_assets.json"

def main():
    print("=" * 40)
    print("🚀 build_scene_assets 独立运行开始")
    print("=" * 40)

    # 1️⃣ 检查 scene_plan 是否存在
    if not SCENE_PLAN_PATH.exists():
        print(f"❌ 未找到 scene_plan.json: {SCENE_PLAN_PATH}")
        sys.exit(1)

    print(f"📥 输入文件: {SCENE_PLAN_PATH}")

    # 2️⃣ 调用 build_scene_assets
    try:
        # 将项目根目录加入sys.path以便导入build_scene_assets.py
        sys.path.insert(0, str(BASE_DIR))
        from build_scene_assets import build_scene_assets
    except Exception as e:
        print("❌ 无法导入 build_scene_assets.py")
        print(e)
        sys.exit(1)

    try:
        build_scene_assets()
    except Exception as e:
        print("❌ build_scene_assets 执行失败")
        print(e)
        sys.exit(1)

    # 3️⃣ 检查输出
    if not SCENE_ASSETS_PATH.exists():
        print("❌ scene_assets.json 未生成")
        sys.exit(1)

    print(f"📤 输出文件: {SCENE_ASSETS_PATH}")

    # 4️⃣ 打印简单统计
    try:
        data = json.loads(SCENE_ASSETS_PATH.read_text(encoding="utf-8"))
        
        # 支持两种格式：list 和 {"scene_assets": [...]}
        if isinstance(data, list):
            assets = data
        elif isinstance(data, dict) and "scene_assets" in data:
            assets = data.get("scene_assets", [])
        else:
            print("⚠️ scene_assets.json 格式不规范")
            return
        
        print(f"📊 场景数量: {len(assets)}")

        if len(assets) > 0:
            print("🔍 示例记录：")
            print(json.dumps(assets[0], indent=2, ensure_ascii=False))
    except Exception as e:
        print("⚠️ 输出文件解析失败")
        print(e)

    print("✅ build_scene_assets 运行完成")

if __name__ == "__main__":
    main()