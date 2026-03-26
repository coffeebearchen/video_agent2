# -*- coding: utf-8 -*-
"""
runner/task14_scene_decision_quality_runner.py

【Task14：scene_decision_quality 最小安全执行器】

作用：
1. 读取 data/current/scene_decision_debug.json
2. 调用质量检查模块进行离线审计
3. 生成 data/current/scene_decision_quality.json
4. 打印最小统计结果

边界：
- 不修改旧主链
- 不修改任何素材决策结果
- 仅做独立质量审计
- 仅使用 Python 标准库
"""

from __future__ import annotations

import sys
from pathlib import Path

# 允许直接运行时找到项目根目录
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.scene_decision_quality_checker import (
    build_scene_decision_quality_payload,
    load_scene_decision_debug,
    save_scene_decision_quality,
)


def main() -> None:
    """主执行入口。"""
    input_file = PROJECT_ROOT / "data" / "current" / "scene_decision_debug.json"
    output_file = PROJECT_ROOT / "data" / "current" / "scene_decision_quality.json"

    print("=" * 60)
    print("开始执行 Task14：生成 scene_decision_quality.json")
    print("=" * 60)
    print(f"输入文件：{input_file}")
    print(f"输出文件：{output_file}")

    debug_data = load_scene_decision_debug(input_file)
    records = debug_data.get("items", [])
    payload = build_scene_decision_quality_payload(records)
    save_scene_decision_quality(payload, output_file)

    summary = payload.get("summary", {})
    print("✅ scene_decision_quality.json 已生成")
    print(f"场景数量：{payload.get('scene_count', 0)}")
    print(f"ok      ：{summary.get('ok_count', 0)}")
    print(f"info    ：{summary.get('info_count', 0)}")
    print(f"warning ：{summary.get('warning_count', 0)}")
    print(f"error   ：{summary.get('error_count', 0)}")
    print(f"fallback：{summary.get('fallback_count', 0)}")
    print("=" * 60)


if __name__ == "__main__":
    main()