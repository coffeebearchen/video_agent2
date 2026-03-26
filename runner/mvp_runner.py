# -*- coding: utf-8 -*-
"""
runner/mvp_runner.py

【作用】
Task1 的最小可运行入口

【功能】
1. 接收一句输入
2. 调用 expression_detector
3. 打印标准结果
4. 保存到 data/current/task1_expression.json

【边界】
- 不改现有主链
- 不调用视频模块
- 不调用素材模块
- 不引入第三方依赖
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# 让脚本可以从项目根目录直接运行
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.expression_detector import detect_expression
from models.schema import Task1Output


def ensure_output_dir() -> Path:
    """
    确保输出目录存在
    """
    output_dir = PROJECT_ROOT / "data" / "current"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def save_result(output: Task1Output, file_path: Path) -> None:
    """
    保存结果到 json 文件
    """
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(output.to_dict(), f, ensure_ascii=False, indent=2)


def print_result(output: Task1Output) -> None:
    """
    打印结果到终端
    """
    print("=" * 60)
    print("Task1 运行结果")
    print("=" * 60)
    print(f"success         : {output.success}")
    print(f"input_text      : {output.input_text}")
    print(f"expression_type : {output.result.expression_type}")
    print(f"carrier         : {output.result.carrier}")
    print(f"core_text       : {output.result.core_text}")
    print(f"confidence      : {output.result.confidence}")
    print("reasons         :")
    for idx, reason in enumerate(output.result.reasons, start=1):
        print(f"  {idx}. {reason}")
    print(f"message         : {output.message}")
    print("=" * 60)


def run_task1(text: str) -> Task1Output:
    """
    执行 Task1 最小链路
    """
    result = detect_expression(text)

    output = Task1Output(
        success=True,
        input_text=text,
        result=result,
        message="Task1 运行成功：expression_detector 已完成最小识别。"
    )

    output_dir = ensure_output_dir()
    output_file = output_dir / "task1_expression.json"
    save_result(output, output_file)

    return output


def main() -> None:
    """
    命令行入口

    用法1：
        python runner/mvp_runner.py

    用法2：
        python runner/mvp_runner.py "为什么利率会影响资产价格？"
    """
    try:
        if len(sys.argv) > 1:
            input_text = " ".join(sys.argv[1:]).strip()
        else:
            print("请输入一句话：")
            input_text = input("> ").strip()

        if not input_text:
            raise ValueError("输入不能为空。")

        output = run_task1(input_text)
        print_result(output)

        output_file = PROJECT_ROOT / "data" / "current" / "task1_expression.json"
        print(f"结果已保存：{output_file}")

    except Exception as e:
        print("=" * 60)
        print("Task1 运行失败")
        print("=" * 60)
        print(f"错误信息：{e}")
        print("=" * 60)
        raise


if __name__ == "__main__":
    main()