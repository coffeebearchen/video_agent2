# -*- coding: utf-8 -*-
"""
runner/task26_scene_decision_patch_preview_runner.py

【Patch Preview：scene_decision_patch_preview 最小安全执行器】

作用：
1. 读取 scene_assets.json 和 safe_patch_plan.json
2. 生成 scene_decision_patch_preview.json
3. 打印最小统计结果

边界：
- 不修改任何输入文件
- 不执行任何真实 patch
- 不依赖渲染主流程
"""

from __future__ import annotations

import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.scene_decision_patch_preview_builder import (
    build_patch_preview,
    load_preview_inputs,
    save_patch_preview,
)


def main() -> int:
    """主执行入口。"""
    base_dir = PROJECT_ROOT / "data" / "current"
    scene_assets_file = base_dir / "scene_assets.json"
    patch_plan_file = base_dir / "scene_decision_safe_patch_plan.json"
    output_file = base_dir / "scene_decision_patch_preview.json"

    print("=" * 60)
    print("开始执行 Patch Preview：生成 scene_decision_patch_preview.json")
    print("=" * 60)
    print(f"scene_assets 输入：{scene_assets_file}")
    print(f"patch_plan 输入：{patch_plan_file}")
    print(f"输出文件：{output_file}")

    try:
        original_scene_assets, patch_plan = load_preview_inputs(scene_assets_file, patch_plan_file)
        payload = build_patch_preview(original_scene_assets, patch_plan)
        save_patch_preview(payload, output_file)
    except FileNotFoundError as error:
        print(f"❌ 输入文件缺失：{error}")
        print("该错误仅影响 Patch Preview 预览输出，不影响旧主链。")
        return 1
    except Exception as error:  # pragma: no cover - 独立 runner 安全提示
        print(f"❌ Patch Preview 执行失败：{error}")
        print("该错误仅影响 Patch Preview 预览输出，不影响旧主链。")
        return 1

    print("✅ scene_decision_patch_preview.json 已生成")
    print(f"原始 scene 数：{payload.get('original_scene_assets_count', 0)}")
    print(f"patch 后 scene 数：{payload.get('patched_scene_assets_count', 0)}")
    print(f"patch 数量：{payload.get('patch_item_count', 0)}")
    print(f"变更项数量：{payload.get('changed_item_count', 0)}")
    print(f"跳过 patch 数量：{payload.get('skipped_patch_count', 0)}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())