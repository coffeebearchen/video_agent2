# -*- coding: utf-8 -*-
"""
runner/task23_scene_decision_execution_target_resolver_runner.py

【Task23：scene_decision_execution_target_resolver 最小安全执行器】

作用：
1. 读取 action_plan / human_execution_interface / execution_log
2. 生成 scene_decision_execution_targets.json
3. 打印最小统计结果

边界：
- 不执行任何真实动作
- 不修改主链
- 不修改任何输入 JSON
- 仅做候选目标解析输出
"""

from __future__ import annotations

import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.scene_decision_execution_target_resolver import (
    build_execution_targets,
    load_execution_target_inputs,
    save_execution_targets,
)


def main() -> int:
    """主执行入口。"""
    base_dir = PROJECT_ROOT / "data" / "current"
    action_plan_file = base_dir / "scene_decision_action_plan.json"
    human_interface_file = base_dir / "scene_decision_human_execution_interface.json"
    execution_log_file = base_dir / "scene_decision_execution_log.json"
    output_file = base_dir / "scene_decision_execution_targets.json"

    print("=" * 60)
    print("开始执行 Task23：生成 scene_decision_execution_targets.json")
    print("=" * 60)
    print(f"action_plan 输入：{action_plan_file}")
    print(f"human_interface 输入：{human_interface_file}")
    print(f"execution_log 输入：{execution_log_file}")
    print(f"输出文件：{output_file}")

    try:
        loaded_inputs = load_execution_target_inputs(
            action_plan_file,
            human_interface_file,
            execution_log_file,
        )
        payload = build_execution_targets(loaded_inputs)
        save_execution_targets(payload, output_file)
    except FileNotFoundError as error:
        print(f"❌ 输入文件缺失：{error}")
        print("该错误仅影响 Task23 目标解析生成，不影响旧主链。")
        return 1
    except Exception as error:  # pragma: no cover - 独立 runner 安全提示
        print(f"❌ Task23 执行失败：{error}")
        print("该错误仅影响 Task23 目标解析生成，不影响旧主链。")
        return 1

    summary = payload.get("summary", {})
    print("✅ scene_decision_execution_targets.json 已生成")
    print(f"目标条目数：{payload.get('total_target_items', 0)}")
    print(f"高置信度数量：{summary.get('high_confidence_count', 0)}")
    print(f"中置信度数量：{summary.get('medium_confidence_count', 0)}")
    print(f"低置信度数量：{summary.get('low_confidence_count', 0)}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())