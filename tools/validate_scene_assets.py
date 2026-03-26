# -*- coding: utf-8 -*-
"""
tools/validate_scene_assets.py

作用：
验证 scene_assets.json 结构是否合法
"""

import json
from pathlib import Path
import sys

REQUIRED_FIELDS = ["type", "duration"]

BASE_DIR = Path(__file__).resolve().parent.parent
SCENE_ASSETS_PATH = BASE_DIR / "data" / "current" / "scene_assets.json"


def validate():
    if not SCENE_ASSETS_PATH.exists():
        print("❌ scene_assets.json 不存在")
        sys.exit(1)

    data = json.loads(SCENE_ASSETS_PATH.read_text(encoding="utf-8"))

    # 支持两种格式：list 和 {"scene_assets": [...]}
    if isinstance(data, list):
        assets = data
    elif isinstance(data, dict) and "scene_assets" in data:
        assets = data.get("scene_assets", [])
    else:
        print("❌ scene_assets.json 格式错误（应为 list 或 {'scene_assets': [...]}）")
        sys.exit(1)

    if not assets:
        print("❌ scene_assets.json 为空")
        sys.exit(1)

    for i, item in enumerate(assets):
        for field in REQUIRED_FIELDS:
            if field not in item:
                print(f"❌ 第 {i} 条缺少字段: {field}")
                sys.exit(1)

        if not isinstance(item["duration"], (int, float)):
            print(f"❌ 第 {i} 条 duration 类型错误")
            sys.exit(1)

    print("✅ scene_assets.json 验证通过")


if __name__ == "__main__":
    validate()