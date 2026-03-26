# -*- coding: utf-8 -*-
"""
runner/task20_scene_decision_manual_trigger_plan_runner.py

【Task20：scene_decision_manual_trigger_plan 最小安全执行器】

作用：
1. 读取 data/current/scene_decision_human_execution_interface.json
2. 生成人工触发清单文件
3. 打印最小统计结果

边界：
- 不自动执行任何 action
- 不修改主链
- 不修改任何输入 JSON
- 仅做人机触发层输出
"""

from __future__ import annotations

import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.scene_decision_manual_trigger_plan_builder import (
    build_manual_trigger_plan,
    load_scene_decision_human_execution_interface,
    save_scene_decision_manual_trigger_plan,
)


def main() -> int:
    """主执行入口。"""
    input_file = PROJECT_ROOT / "data" / "current" / "scene_decision_human_execution_interface.json"
    output_file = PROJECT_ROOT / "data" / "current" / "scene_decision_manual_trigger_plan.json"

    print("=" * 60)
    print("开始执行 Task20：生成 scene_decision_manual_trigger_plan.json")
    print("=" * 60)
    print(f"输入文件：{input_file}")
    print(f"输出文件：{output_file}")

    try:
        interface_data = load_scene_decision_human_execution_interface(input_file)
        payload = build_manual_trigger_plan(interface_data)
        save_scene_decision_manual_trigger_plan(payload, output_file)
    except FileNotFoundError as error:
        print(f"❌ 输入文件缺失：{error}")
        print("该错误仅影响 Task20 人工触发清单生成，不影响旧主链。")
        return 1
    except Exception as error:  # pragma: no cover - 独立 runner 安全提示
        print(f"❌ Task20 执行失败：{error}")
        print("该错误仅影响 Task20 人工触发清单生成，不影响旧主链。")
        return 1

    print("✅ scene_decision_manual_trigger_plan.json 已生成")
    print(f"场景数量：{payload.get('scene_count', 0)}")
    print(f"整体状态：{payload.get('overall_status', 'stable')}")
    print(f"可触发数量：{payload.get('triggerable_count', 0)}")
    print(f"阻断数量：{payload.get('blocked_count', 0)}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())