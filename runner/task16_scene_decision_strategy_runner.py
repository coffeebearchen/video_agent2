# -*- coding: utf-8 -*-
"""
runner/task16_scene_decision_strategy_runner.py

【Task16：scene_decision_strategy 最小安全执行器】

作用：
1. 读取 data/current/scene_decision_feedback.json
2. 调用 strategy 模块聚合系统级建议
3. 输出 data/current/scene_decision_strategy.json
4. 打印最小统计结果

边界：
- 不修改旧主链
- 不修改任何现有决策结果
- 仅做独立策略聚合
- 仅使用 Python 标准库
"""

from __future__ import annotations

import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.scene_decision_strategy_builder import (
    build_scene_decision_strategy_payload,
    load_scene_decision_feedback,
    save_scene_decision_strategy,
)


def main() -> None:
    """主执行入口。"""
    input_file = PROJECT_ROOT / "data" / "current" / "scene_decision_feedback.json"
    output_file = PROJECT_ROOT / "data" / "current" / "scene_decision_strategy.json"

    print("=" * 60)
    print("开始执行 Task16：生成 scene_decision_strategy.json")
    print("=" * 60)
    print(f"输入文件：{input_file}")
    print(f"输出文件：{output_file}")

    feedback_data = load_scene_decision_feedback(input_file)
    feedback_items = feedback_data.get("items", [])
    payload = build_scene_decision_strategy_payload(feedback_items)
    save_scene_decision_strategy(payload, output_file)

    summary = payload.get("summary", {})
    print("✅ scene_decision_strategy.json 已生成")
    print(f"场景数量：{payload.get('scene_count', 0)}")
    print(f"反馈总数：{summary.get('total_feedback_count', 0)}")
    print(f"受影响场景：{summary.get('affected_scene_count', 0)}")
    print(f"主导策略：{summary.get('dominant_strategy', 'none')}")
    print("=" * 60)


if __name__ == "__main__":
    main()