# -*- coding: utf-8 -*-
"""
runner/task2_expression_runner.py

【Task2：expression.json 最小安全执行器】

作用：
1. 读取 data/current/script.json
2. 提取其中可用的文本内容
3. 调用 Task1 的 expression_detector
4. 生成 data/current/expression.json

边界：
- 不修改任何旧主链文件
- 不接入 scene / timing / assets
- 仅作为外挂层输出 expression.json
- 仅使用 Python 标准库
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# 允许直接运行时找到项目根目录
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.expression_detector import detect_expression  # type: ignore


def load_json(file_path: Path) -> Any:
    """读取 JSON 文件"""
    if not file_path.exists():
        raise FileNotFoundError(f"❌ 文件不存在：{file_path}")

    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(file_path: Path, data: Any) -> None:
    """保存 JSON 文件"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def extract_text_items(script_data: Any) -> List[str]:
    """
    从 script.json 中提取文本列表

    兼容优先级：
    A. {"cards": [{"text": "..."}]}
    B. {"scenes": [{"text": "..."}]}
    C. {"script": "..."}
    D. 直接字符串
    """
    text_items: List[str] = []

    # D. 直接字符串
    if isinstance(script_data, str):
        text = script_data.strip()
        if text:
            return [text]

    # 字典结构处理
    if isinstance(script_data, dict):
        # A. cards[*].text
        cards = script_data.get("cards")
        if isinstance(cards, list):
            for item in cards:
                if isinstance(item, dict):
                    text = str(item.get("text", "")).strip()
                    if text:
                        text_items.append(text)
            if text_items:
                return text_items

        # B. scenes[*].text
        scenes = script_data.get("scenes")
        if isinstance(scenes, list):
            for item in scenes:
                if isinstance(item, dict):
                    text = str(item.get("text", "")).strip()
                    if text:
                        text_items.append(text)
            if text_items:
                return text_items

        # C. script
        script_text = script_data.get("script")
        if isinstance(script_text, str):
            script_text = script_text.strip()
            if script_text:
                return [script_text]

    raise ValueError("❌ script.json 中未找到可提取文本内容")


def build_expression_items(text_items: List[str]) -> List[Dict[str, Any]]:
    """对每条文本调用 expression_detector，生成标准输出"""
    results: List[Dict[str, Any]] = []

    for index, text in enumerate(text_items):
        expression_result = detect_expression(text)

        results.append(
            {
                "index": index,
                "source_text": text,
                "expression": expression_result.to_dict(),
            }
        )

    return results


def main() -> None:
    """主执行入口"""
    input_file = PROJECT_ROOT / "data" / "current" / "script.json"
    output_file = PROJECT_ROOT / "data" / "current" / "expression.json"

    print("=" * 60)
    print("开始执行 Task2：生成 expression.json")
    print("=" * 60)
    print(f"输入文件：{input_file}")
    print(f"输出文件：{output_file}")

    script_data = load_json(input_file)
    text_items = extract_text_items(script_data)

    print(f"已提取文本条数：{len(text_items)}")

    items = build_expression_items(text_items)

    output_data = {
        "source_file": "data/current/script.json",
        "output_file": "data/current/expression.json",
        "total_items": len(items),
        "items": items,
    }

    save_json(output_file, output_data)

    print("✅ expression.json 已生成")
    print(f"输出路径：{output_file}")
    print(f"总条数：{len(items)}")
    print("=" * 60)


if __name__ == "__main__":
    main()