# -*- coding: utf-8 -*-
"""
asset_selector.py

【素材选择兼容入口｜纯转发版】

作用：
1. 保留旧接口名与旧调用方式不变
2. 直接转发到 modules.asset_selector
3. 保留最小返回结构校验
4. 新模块异常时明确报错，不再 fallback

返回格式：
{
    "matched": True/False,
    "asset_type": "image" | "text_card",
    "asset_file": "资源文件路径或空字符串",
    "keyword": "命中的关键词",
    "reason": "匹配理由"
}
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from modules import project_paths

try:
    from modules.asset_selector import select_asset_for_text as new_select_asset_for_text
except Exception as error:
    new_select_asset_for_text = None
    NEW_SELECTOR_IMPORT_ERROR = error
else:
    NEW_SELECTOR_IMPORT_ERROR = None


def _validate_main_result(result: Any) -> bool:
    if not isinstance(result, dict):
        return False

    required_fields = ["matched", "asset_type", "asset_file", "reason"]
    for field_name in required_fields:
        if field_name not in result:
            return False

    asset_file = str(result.get("asset_file", "") or "").strip()
    if asset_file:
        asset_path = Path(asset_file)
        if not asset_path.is_absolute():
            asset_path = project_paths.get_project_root() / asset_path
        if not asset_path.exists():
            return False

    return True


def select_asset_for_text(text: str) -> Dict[str, Any]:
    """兼容旧入口，直接转发到新模块。"""
    try:
        if new_select_asset_for_text is None:
            raise RuntimeError(f"新模块不可用: {NEW_SELECTOR_IMPORT_ERROR}")

        result = new_select_asset_for_text(text)
        if not _validate_main_result(result):
            raise ValueError("新模块返回结构非法")
    except Exception as error:
        print(f"[ASSET][MAIN][ERROR] 新模块异常: {error}")
        raise

    print("[ASSET][MAIN] 使用新模块")
    return result


if __name__ == "__main__":
    test_result = select_asset_for_text("wow")
    print(test_result)
