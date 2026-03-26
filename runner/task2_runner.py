# -*- coding: utf-8 -*-
"""
runner/task2_runner.py

【作用】
Task2 的最小可运行入口

【功能】
1. 接收一句输入
2. 调用 expression_detector
3. 调用 orchestrator
4. 打印结果
5. 保存到 data/current/task2_scene_plan.json

【边界】
- 不改现有主链
- 不调用视频模块
- 不调用素材模块
- 不引入第三方依赖
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# 让脚本可以从项目根目录直接运行
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.expression_detector import detect_expression
from core.orchestrator import build_scene_plan
from models.scene_schema import Task2Output


def ensure_output_dir() -> Path:
    """
    确保输出目录存在
    """
    output_dir = PROJECT_ROOT / "data" / "current"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def save_result(output: Task2Output, file_path: Path) -> None:
    """
    保存结果到 json 文件
    """
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(output.to_dict(), f, ensure_ascii=False, indent=2)


def print_result(output: Task2Output) -> None:
    """
    打印结果到终端
    """
    print("=" * 60)
    print("Task2 运行结果")
    print("=" * 60)
    print(f"success         : {output.success}")
    print(f"input_text      : {output.input_text}")
    print(f"expression_type : {output.expression_type}")
    print(f"carrier         : {output.carrier}")
    print(f"scene_count     : {len(output.scene_plan.scenes)}")
    print("scenes          :")

    for scene in output.scene_plan.scenes:
        print(f"  - scene_id   : {scene.scene_id}")
        print(f"    scene_type : {scene.scene_type}")
        print(f"    duration   : {scene.duration}")
        print(f"    source     : {scene.source}")
        print(f"    text       : {scene.text}")

    print(f"message         : {output.message}")
    print("=" * 60)


def run_task2(text: str) -> Task2Output:
    """
    执行 Task2 最小链路
    """
    expression_result = detect_expression(text)
    scene_plan = build_scene_plan(input_text=text, expression_result=expression_result)

    output = Task2Output(
        success=True,
        input_text=text,
        expression_type=expression_result.expression_type,
        carrier=expression_result.carrier,
        scene_plan=scene_plan,
        message="Task2 运行成功：orchestrator 已完成最小场景组织。"
    )

    output_dir = ensure_output_dir()
    output_file = output_dir / "task2_scene_plan.json"
    save_result(output, output_file)

    return output


def main() -> None:
    """
    命令行入口

    用法1：
        python runner/task2_runner.py

    用法2：
        python runner/task2_runner.py "为什么利率会影响资产价格？"
    """
    try:
        if len(sys.argv) > 1:
            input_text = " ".join(sys.argv[1:]).strip()
        else:
            print("请输入一句话：")
            input_text = input("> ").strip()

        if not input_text:
            raise ValueError("输入不能为空。")

        output = run_task2(input_text)
        print_result(output)

        output_file = PROJECT_ROOT / "data" / "current" / "task2_scene_plan.json"
        print(f"结果已保存：{output_file}")

    except Exception as e:
        print("=" * 60)
        print("Task2 运行失败")
        print("=" * 60)
        print(f"错误信息：{e}")
        print("=" * 60)
        raise


if __name__ == "__main__":
    main()