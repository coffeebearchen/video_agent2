# -*- coding: utf-8 -*-
"""
runner/task17_scene_decision_strategy_review_runner.py

【Task17：scene_decision_strategy_review 最小安全执行器】

作用：
1. 读取 data/current/scene_decision_strategy.json
2. 生成人工可读的 scene_decision_strategy_review.json
3. 打印最小统计结果

边界：
- 不修改旧主链
- 不修改任何现有决策结果
- 不参与渲染流程
- 仅做策略复核报告输出
"""

from __future__ import annotations

import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.scene_decision_strategy_review_builder import (
    build_strategy_review_payload,
    load_scene_decision_strategy,
    save_scene_decision_strategy_review,
)


def main() -> int:
    """主执行入口。"""
    input_file = PROJECT_ROOT / "data" / "current" / "scene_decision_strategy.json"
    output_file = PROJECT_ROOT / "data" / "current" / "scene_decision_strategy_review.json"

    print("=" * 60)
    print("开始执行 Task17：生成 scene_decision_strategy_review.json")
    print("=" * 60)
    print(f"输入文件：{input_file}")
    print(f"输出文件：{output_file}")

    try:
        strategy_data = load_scene_decision_strategy(input_file)
        payload = build_strategy_review_payload(strategy_data)
        save_scene_decision_strategy_review(payload, output_file)
    except FileNotFoundError as error:
        print(f"❌ 输入文件缺失：{error}")
        print("该错误仅影响 Task17 独立报告生成，不影响旧主链。")
        return 1
    except Exception as error:  # pragma: no cover - 独立 runner 的安全提示
        print(f"❌ Task17 执行失败：{error}")
        print("该错误仅影响 Task17 独立报告生成，不影响旧主链。")
        return 1

    print("✅ scene_decision_strategy_review.json 已生成")
    print(f"场景数量：{payload.get('scene_count', 0)}")
    print(f"整体状态：{payload.get('overall_status', 'stable')}")
    print(f"主导策略：{payload.get('dominant_strategy', 'none')}")
    print(f"复核条目数：{len(payload.get('review_items', []))}")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())