# -*- coding: utf-8 -*-
"""
image_ai_generator.py
========================================================
作用：
1. AI 生图模块默认关闭
2. 只有在“手动开启 + 收费确认”同时满足时，才允许继续
3. 当前版本不接入主链
4. 当前版本只负责“开关控制 + 解释拦截”

设计原则：
- 默认关闭，避免误触发费用
- 不进入当前主链
- 后续如需正式接入，再补真实生图 API 调用
"""

import os
import json
from typing import Dict, Any


CONFIG_FILE = "project_config.json"


DEFAULT_AI_IMAGE_POLICY = {
    "enabled": False,
    "require_paid_confirmation": True,
    "payment_confirmed": False,
    "message": "AI 生图默认关闭；只有在用户收费确认后，才允许手动开启。"
}


def safe_read_json(path: str, default: Any) -> Any:
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


def load_ai_image_policy(config_file: str = CONFIG_FILE) -> Dict[str, Any]:
    """
    从 project_config.json 读取 AI 生图开关。
    如果没有配置，默认关闭。
    """
    cfg = safe_read_json(config_file, {})
    if not isinstance(cfg, dict):
        cfg = {}

    features = cfg.get("features", {})
    if not isinstance(features, dict):
        features = {}

    ai_image = features.get("ai_image", {})
    if not isinstance(ai_image, dict):
        ai_image = {}

    result = DEFAULT_AI_IMAGE_POLICY.copy()
    result.update(ai_image)
    return result


def explain_ai_image_policy() -> str:
    """
    返回当前 AI 生图模块的业务解释说明。
    """
    return (
        "当前 AI 生图模块默认关闭，原因如下：\n"
        "1. 生图费用不可控，容易误触发；\n"
        "2. 当前主链采用“图库 + 标签 + 索引 + 自动选图”路线；\n"
        "3. 当前阶段优先保证主链稳定，不把 AI 生图接入正式流程；\n"
        "4. 只有在用户明确收费确认后，才允许人工手动开启。"
    )


def assert_ai_image_allowed() -> None:
    """
    检查 AI 生图是否允许使用。
    必须满足：
    1. enabled = True
    2. payment_confirmed = True（如果 require_paid_confirmation = True）
    """
    policy = load_ai_image_policy()

    enabled = bool(policy.get("enabled", False))
    require_paid_confirmation = bool(policy.get("require_paid_confirmation", True))
    payment_confirmed = bool(policy.get("payment_confirmed", False))

    if not enabled:
        raise RuntimeError(
            "AI 生图模块当前处于关闭状态。\n\n"
            f"{explain_ai_image_policy()}\n\n"
            "如需启用，请先在 project_config.json 中手动设置：\n"
            "features.ai_image.enabled = true\n"
            "并完成收费确认。"
        )

    if require_paid_confirmation and not payment_confirmed:
        raise RuntimeError(
            "AI 生图模块已被手动开启，但尚未完成收费确认，当前仍禁止使用。\n\n"
            "启用条件：\n"
            "1. features.ai_image.enabled = true\n"
            "2. features.ai_image.payment_confirmed = true\n\n"
            "只有这两个条件同时满足，才允许继续。"
        )


def generate_background(prompt: str, output_path: str) -> str:
    """
    当前版本只做“开关控制”。
    如果未来要正式接入真实 AI 生图 API，再在这里补具体调用逻辑。
    """
    assert_ai_image_allowed()

    raise RuntimeError(
        "AI 生图模块的收费开关已经通过，但当前版本仍未接入正式主链。\n"
        "当前项目冻结路线为：图库 + 标签 + 索引 + 自动选图。\n"
        "如后续确需商用启用 AI 生图，再单独接入真实 API。"
    )


if __name__ == "__main__":
    try:
        policy = load_ai_image_policy()
        print("=== AI IMAGE POLICY ===")
        print(json.dumps(policy, ensure_ascii=False, indent=2))
        print("")
        print(explain_ai_image_policy())
    except Exception as e:
        print(str(e))