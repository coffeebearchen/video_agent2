# -*- coding: utf-8 -*-
"""
runner/task15_scene_decision_feedback_runner.py

【Task15：scene_decision_feedback 最小安全执行器】

作用：
1. 读取 data/current/scene_decision_quality.json
2. 调用 feedback 模块生成建议
3. 输出 data/current/scene_decision_feedback.json
4. 打印最小统计结果

边界：
- 不修改旧主链
- 不修改任何现有决策结果
- 仅做独立反馈生成
- 仅使用 Python 标准库
"""

from __future__ import annotations

import sys
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.scene_decision_feedback_builder import (
    build_scene_decision_feedback_payload,
    load_scene_decision_quality,
    save_scene_decision_feedback,
)


def main() -> None:
    """主执行入口。"""
    input_file = PROJECT_ROOT / "data" / "current" / "scene_decision_quality.json"
    output_file = PROJECT_ROOT / "data" / "current" / "scene_decision_feedback.json"

    print("=" * 60)
    print("开始执行 Task15：生成 scene_decision_feedback.json")
    print("=" * 60)
    print(f"输入文件：{input_file}")
    print(f"输出文件：{output_file}")

    quality_data = load_scene_decision_quality(input_file)
    quality_items = quality_data.get("items", [])
    payload = build_scene_decision_feedback_payload(quality_items)
    save_scene_decision_feedback(payload, output_file)

    summary = payload.get("summary", {})
    print("✅ scene_decision_feedback.json 已生成")
    print(f"场景数量：{payload.get('scene_count', 0)}")
    print(f"反馈总数：{summary.get('total_feedback_count', 0)}")
    print(f"含反馈场景：{summary.get('scene_with_feedback_count', 0)}")
    print(f"high   ：{summary.get('high_priority_count', 0)}")
    print(f"medium ：{summary.get('medium_priority_count', 0)}")
    print(f"low    ：{summary.get('low_priority_count', 0)}")
    print("=" * 60)


if __name__ == "__main__":
    main()