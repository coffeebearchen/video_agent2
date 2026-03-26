# -*- coding: utf-8 -*-
"""
runner/task24_scene_decision_safe_patch_plan_runner.py

【Task24：scene_decision_safe_patch_plan 最小安全执行器】

作用：
1. 读取 scene_decision_execution_targets.json
2. 生成 scene_decision_safe_patch_plan.json
3. 打印最小统计结果

边界：
- 不执行任何 patch
- 不修改主链
- 不修改任何输入 JSON
- 仅做 patch 草案输出
"""

from __future__ import annotations

import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.scene_decision_safe_patch_plan_builder import (
    build_safe_patch_plan,
    load_execution_targets,
    save_safe_patch_plan,
)


def main() -> int:
    """主执行入口。"""
    input_file = PROJECT_ROOT / "data" / "current" / "scene_decision_execution_targets.json"
    output_file = PROJECT_ROOT / "data" / "current" / "scene_decision_safe_patch_plan.json"

    print("=" * 60)
    print("开始执行 Task24：生成 scene_decision_safe_patch_plan.json")
    print("=" * 60)
    print(f"输入文件：{input_file}")
    print(f"输出文件：{output_file}")

    try:
        targets_data = load_execution_targets(input_file)
        payload = build_safe_patch_plan(targets_data)
        save_safe_patch_plan(payload, output_file)
    except FileNotFoundError as error:
        print(f"❌ 输入文件缺失：{error}")
        print("该错误仅影响 Task24 patch 草案生成，不影响旧主链。")
        return 1
    except Exception as error:  # pragma: no cover - 独立 runner 安全提示
        print(f"❌ Task24 执行失败：{error}")
        print("该错误仅影响 Task24 patch 草案生成，不影响旧主链。")
        return 1

    summary = payload.get("summary", {})
    print("✅ scene_decision_safe_patch_plan.json 已生成")
    print(f"patch 条目数：{payload.get('total_patch_items', 0)}")
    print(f"draft 数量：{summary.get('draft_count', 0)}")
    print(f"update 数量：{summary.get('update_count', 0)}")
    print(f"append 数量：{summary.get('append_count', 0)}")
    print(f"monitor_only 数量：{summary.get('monitor_only_count', 0)}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())