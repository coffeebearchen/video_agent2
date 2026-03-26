# -*- coding: utf-8 -*-
"""
runner/task18_scene_decision_action_plan_runner.py

【Task18：scene_decision_action_plan 最小安全执行器】

作用：
1. 读取 strategy 或 review
2. 生成 scene_decision_action_plan.json
3. 打印摘要信息

边界：
- 不修改主链
- 不自动执行任何动作
- 不修改任何输入 JSON
- 仅生成执行接口层模板
"""

from __future__ import annotations

import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.scene_decision_action_plan_builder import (
    build_action_plan,
    load_strategy_or_review,
    save_action_plan,
)


def main() -> int:
    """主执行入口。"""
    strategy_file = PROJECT_ROOT / "data" / "current" / "scene_decision_strategy.json"
    review_file = PROJECT_ROOT / "data" / "current" / "scene_decision_strategy_review.json"
    output_file = PROJECT_ROOT / "data" / "current" / "scene_decision_action_plan.json"

    print("=" * 60)
    print("开始执行 Task18：生成 scene_decision_action_plan.json")
    print("=" * 60)
    print(f"策略输入：{strategy_file}")
    print(f"复核输入：{review_file}")
    print(f"输出文件：{output_file}")

    try:
        loaded_input = load_strategy_or_review(strategy_file, review_file)
        payload = build_action_plan(loaded_input)
        save_action_plan(payload, output_file)
    except FileNotFoundError as error:
        print(f"❌ 输入文件缺失：{error}")
        print("该错误仅影响 Task18 独立 action_plan 生成，不影响旧主链。")
        return 1
    except Exception as error:  # pragma: no cover - 独立 runner 的安全提示
        print(f"❌ Task18 执行失败：{error}")
        print("该错误仅影响 Task18 独立 action_plan 生成，不影响旧主链。")
        return 1

    print("✅ scene_decision_action_plan.json 已生成")
    print(f"场景数量：{payload.get('scene_count', 0)}")
    print(f"整体状态：{payload.get('overall_status', 'stable')}")
    print(f"动作条目数：{len(payload.get('action_items', []))}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())