# -*- coding: utf-8 -*-
"""
runner/task22_scene_decision_execution_log_runner.py

【Task22：scene_decision_execution_log 最小安全执行器】

作用：
1. 读取 human_execution_interface / manual_trigger_plan / dry_run_result
2. 生成 scene_decision_execution_log.json
3. 打印最小统计结果

边界：
- 不执行任何真实 action
- 不修改主链
- 不修改任何输入 JSON
- 仅做执行日志输出
"""

from __future__ import annotations

import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.scene_decision_execution_log_builder import (
    build_execution_log,
    load_execution_layer_inputs,
    save_execution_log,
)


def main() -> int:
    """主执行入口。"""
    base_dir = PROJECT_ROOT / "data" / "current"
    human_file = base_dir / "scene_decision_human_execution_interface.json"
    trigger_file = base_dir / "scene_decision_manual_trigger_plan.json"
    dry_run_file = base_dir / "scene_decision_dry_run_result.json"
    output_file = base_dir / "scene_decision_execution_log.json"

    print("=" * 60)
    print("开始执行 Task22：生成 scene_decision_execution_log.json")
    print("=" * 60)
    print(f"人工接口输入：{human_file}")
    print(f"触发清单输入：{trigger_file}")
    print(f"dry-run 输入：{dry_run_file}")
    print(f"输出文件：{output_file}")

    try:
        loaded_inputs = load_execution_layer_inputs(human_file, trigger_file, dry_run_file)
        payload = build_execution_log(loaded_inputs)
        save_execution_log(payload, output_file)
    except FileNotFoundError as error:
        print(f"❌ 输入文件缺失：{error}")
        print("该错误仅影响 Task22 执行日志生成，不影响旧主链。")
        return 1
    except Exception as error:  # pragma: no cover - 独立 runner 安全提示
        print(f"❌ Task22 执行失败：{error}")
        print("该错误仅影响 Task22 执行日志生成，不影响旧主链。")
        return 1

    summary = payload.get("summary", {})
    print("✅ scene_decision_execution_log.json 已生成")
    print(f"日志条目数：{payload.get('total_log_items', 0)}")
    print(f"待审批数量：{summary.get('pending_approval_count', 0)}")
    print(f"可触发数量：{summary.get('ready_to_trigger_count', 0)}")
    print(f"阻断数量：{summary.get('blocked_count', 0)}")
    print(f"仅 dry-run 数量：{summary.get('dry_run_only_count', 0)}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())