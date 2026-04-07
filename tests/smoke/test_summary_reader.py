#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Summary Reader Smoke Test V1
目标：验证 batch_summary.json 是否满足稳定读取、无防御性字段判断的要求。

文件位置：tests/smoke/test_summary_reader.py
输入来源：output/batch_generation/batch_summary.json
运行方式：python tests/smoke/test_summary_reader.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# 定位项目根目录（tests/smoke/ 向上两级）
PROJECT_ROOT = Path(__file__).resolve().parents[2]
SUMMARY_PATH = PROJECT_ROOT / "output" / "batch_generation" / "batch_summary.json"


def load_summary() -> Dict[str, Any] | None:
    """加载 summary 文件。
    
    返回：
        - 成功：dict 对象
        - 失败：None
    """
    if not SUMMARY_PATH.exists():
        print(f"[FAIL] summary file not found: {SUMMARY_PATH}")
        return None

    try:
        with open(SUMMARY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"[FAIL] json parse error: {e}")
        return None
    except Exception as e:
        print(f"[FAIL] read file error: {e}")
        return None


def validate_top_level(summary: Dict[str, Any]) -> bool:
    """验证顶层字段完整性。
    
    要求：mode, total_inputs, total_styles, total_jobs, success_count, 
    failed_count, output_root, generated_at, items 必须全部存在
    """
    required_fields = [
        "mode",
        "total_inputs",
        "total_styles",
        "total_jobs",
        "success_count",
        "failed_count",
        "output_root",
        "generated_at",
        "items",
    ]

    for field in required_fields:
        if field not in summary:
            print(f"[FAIL] missing top-level field: {field}")
            return False

    print("[OK] top-level schema valid")
    return True


def validate_items(summary: Dict[str, Any]) -> bool:
    """验证 items 结构。
    
    要求：
    - items 必须是数组
    - items 不能为空
    - 每个 item 必须有：item_id, input_index, input_text, status, styles
    - 每个 item 的 styles 必须是非空数组
    """
    items = summary.get("items")

    if not isinstance(items, list):
        print("[FAIL] items is not a list")
        return False

    if len(items) == 0:
        print("[FAIL] items is empty")
        return False

    required_item_fields = ["item_id", "input_index", "input_text", "status", "styles"]

    for idx, item in enumerate(items):
        # 检查字段完整性
        for field in required_item_fields:
            if field not in item:
                print(f"[FAIL] item[{idx}] missing field: {field}")
                return False

        # 验证 styles 是数组
        if not isinstance(item.get("styles"), list):
            print(f"[FAIL] item[{idx}].styles is not a list")
            return False

        if len(item.get("styles", [])) == 0:
            print(f"[FAIL] item[{idx}].styles is empty")
            return False

    print("[OK] items schema valid")
    return True


def validate_styles(summary: Dict[str, Any]) -> bool:
    """验证每个 style 节点字段完整性。
    
    要求：每个 style 必须有：style, status, output_dir, preview_path, meta_path, error
    """
    required_style_fields = ["style", "status", "output_dir", "preview_path", "meta_path", "error"]

    for item_idx, item in enumerate(summary.get("items", [])):
        for style_idx, style in enumerate(item.get("styles", [])):
            for field in required_style_fields:
                if field not in style:
                    print(
                        f"[FAIL] item[{item_idx}].styles[{style_idx}] missing field: {field}"
                    )
                    return False

    print("[OK] style schema valid")
    return True


def validate_status_values(summary: Dict[str, Any]) -> bool:
    """验证状态值合法性。
    
    要求：
    - item.status ∈ {success, failed, partial}
    - style.status ∈ {success, failed}
    """
    valid_item_status = {"success", "failed", "partial"}
    valid_style_status = {"success", "failed"}

    for item_idx, item in enumerate(summary.get("items", [])):
        item_status = item.get("status")
        if item_status not in valid_item_status:
            print(f"[FAIL] item[{item_idx}] invalid status: {item_status}")
            return False

        for style_idx, style in enumerate(item.get("styles", [])):
            style_status = style.get("status")
            if style_status not in valid_style_status:
                print(f"[FAIL] item[{item_idx}].styles[{style_idx}] invalid status: {style_status}")
                return False

    print("[OK] status values valid")
    return True


def validate_counts(summary: Dict[str, Any]) -> bool:
    """验证计数口径一致性。
    
    要求：
    - 实际 items 的总 style 数 == total_jobs
    - success_count + failed_count == total_jobs
    """
    total_jobs = summary.get("total_jobs", 0)
    success_count = summary.get("success_count", 0)
    failed_count = summary.get("failed_count", 0)

    # 计算实际 job 数
    actual_jobs = sum(len(item.get("styles", [])) for item in summary.get("items", []))

    if actual_jobs != total_jobs:
        print(f"[FAIL] total_jobs mismatch: expected {actual_jobs}, got {total_jobs}")
        return False

    if success_count + failed_count != total_jobs:
        print(
            f"[FAIL] counts don't sum to total_jobs: {success_count} + {failed_count} != {total_jobs}"
        )
        return False

    print("[OK] counts valid")
    return True


def run_direct_iteration_check(summary: Dict[str, Any]) -> bool:
    """运行真实的无防御性字段判断遍历测试。
    
    这段代码模拟客户端代码直接读取 summary，不使用任何防御性检查（如 .get() 或 if field in dict）。
    如果任何字段缺失，会直接抛出 KeyError，证明 schema 不够稳定。
    """
    try:
        # === 核心测试：NO .get() 和 NO if field in dict 检查 ===
        # 所有字段必须直接存在，否则抛出异常
        collected = []

        for item in summary["items"]:
            for style_result in item["styles"]:
                # 直接访问关键字段，不用任何防御性判断
                collected.append(
                    {
                        "item_id": item["item_id"],
                        "input_index": item["input_index"],
                        "status": item["status"],
                        "style": style_result["style"],
                        "style_status": style_result["status"],
                        "preview_path": style_result["preview_path"],
                        "meta_path": style_result["meta_path"],
                    }
                )

        if len(collected) == 0:
            print("[FAIL] direct iteration returned no results")
            return False

        print(f"[OK] direct iteration test passed ({len(collected)} results collected)")
        return True

    except KeyError as e:
        print(f"[FAIL] direct iteration failed - missing field: {e}")
        return False
    except Exception as e:
        print(f"[FAIL] direct iteration error: {e}")
        return False


def main() -> None:
    """主验证流程。"""
    print("SUMMARY READER SMOKE TEST")
    print("=" * 70)
    print(f"Reading: {SUMMARY_PATH}")
    print()

    # 1. 加载文件
    summary = load_summary()
    if summary is None:
        print("[FAIL] could not load summary file")
        sys.exit(1)

    if not isinstance(summary, dict):
        print("[FAIL] summary is not a dict")
        sys.exit(1)

    print("[OK] summary file found")
    print("[OK] json parsed")
    print()

    # 2. 按顺序验证
    checks = [
        ("top-level fields", lambda: validate_top_level(summary)),
        ("items structure", lambda: validate_items(summary)),
        ("style schema", lambda: validate_styles(summary)),
        ("status values", lambda: validate_status_values(summary)),
        ("counts", lambda: validate_counts(summary)),
        ("direct iteration", lambda: run_direct_iteration_check(summary)),
    ]

    all_passed = True
    for check_name, check_func in checks:
        if not check_func():
            all_passed = False
            break

    print()
    print("=" * 70)

    if all_passed:
        print("SUMMARY READER SMOKE TEST PASSED")
        sys.exit(0)
    else:
        print("SUMMARY READER SMOKE TEST FAILED")
        sys.exit(1)


if __name__ == "__main__":
    main()
