# -*- coding: utf-8 -*-
"""
runner/task21_scene_decision_dry_run_runner.py

【Task21：scene_decision_dry_run_executor 最小安全执行器】

作用：
1. 读取 data/current/scene_decision_manual_trigger_plan.json
2. 生成 scene_decision_dry_run_result.json
3. 打印最小统计结果

边界：
- 不执行任何真实 action
- 不修改主链
- 不修改任何输入 JSON
- 仅做 dry-run 模拟结果输出
"""

from __future__ import annotations

import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.scene_decision_dry_run_executor import (
    build_dry_run_result,
    load_manual_trigger_plan,
    save_dry_run_result,
)


def main() -> int:
    """主执行入口。"""
    input_file = PROJECT_ROOT / "data" / "current" / "scene_decision_manual_trigger_plan.json"
    output_file = PROJECT_ROOT / "data" / "current" / "scene_decision_dry_run_result.json"

    print("=" * 60)
    print("开始执行 Task21：生成 scene_decision_dry_run_result.json")
    print("=" * 60)
    print(f"输入文件：{input_file}")
    print(f"输出文件：{output_file}")

    try:
        trigger_plan_data = load_manual_trigger_plan(input_file)
        payload = build_dry_run_result(trigger_plan_data)
        save_dry_run_result(payload, output_file)
    except FileNotFoundError as error:
        print(f"❌ 输入文件缺失：{error}")
        print("该错误仅影响 Task21 dry-run 结果生成，不影响旧主链。")
        return 1
    except Exception as error:  # pragma: no cover - 独立 runner 安全提示
        print(f"❌ Task21 执行失败：{error}")
        print("该错误仅影响 Task21 dry-run 结果生成，不影响旧主链。")
        return 1

    print("✅ scene_decision_dry_run_result.json 已生成")
    print(f"场景数量：{payload.get('scene_count', 0)}")
    print(f"模拟执行数：{payload.get('total_simulated', 0)}")
    print(f"跳过数量：{payload.get('total_skipped', 0)}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())