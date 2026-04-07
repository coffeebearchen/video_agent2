# -*- coding: utf-8 -*-
"""
文件名：llm_client.py
作用说明：
1. 提供最小模型调用能力
2. 只负责把 prompt 发给模型并返回原始文本
3. 不承担 prompt 拼装、业务规则、输出纠偏
"""

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"
API_CONFIG_PATH = Path(__file__).resolve().parent.parent / "api_config.json"
DEFAULT_PROVIDER = "deepseek"
DEFAULT_MODEL = "deepseek-chat"
DEFAULT_BASE_URL = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_TIMEOUT = 5


def _load_json_file(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _load_runtime_settings() -> dict[str, Any]:
    config = _load_json_file(CONFIG_PATH)
    api_config = _load_json_file(API_CONFIG_PATH)
    ai_config = config.get("ai_candidate", {}) if isinstance(config, dict) else {}

    provider = str(
        ai_config.get("provider")
        or api_config.get("provider")
        or os.getenv("DEEPSEEK_PROVIDER")
        or DEFAULT_PROVIDER
    ).strip().lower()
    model = str(
        ai_config.get("model")
        or api_config.get("model")
        or os.getenv("DEEPSEEK_MODEL")
        or DEFAULT_MODEL
    ).strip()
    base_url = str(
        ai_config.get("base_url")
        or api_config.get("base_url")
        or os.getenv("DEEPSEEK_BASE_URL")
        or DEFAULT_BASE_URL
    ).strip()

    timeout_value = ai_config.get("timeout")
    if timeout_value is None:
        timeout_value = api_config.get("timeout")
    if timeout_value is None:
        timeout_value = os.getenv("DEEPSEEK_TIMEOUT")
    try:
        timeout = max(1, int(timeout_value if timeout_value is not None else DEFAULT_TIMEOUT))
    except Exception:
        timeout = DEFAULT_TIMEOUT

    api_key = str(
        ai_config.get("api_key")
        or api_config.get("api_key")
        or os.getenv("DEEPSEEK_API_KEY")
        or ""
    ).strip()

    return {
        "provider": provider or DEFAULT_PROVIDER,
        "model": model or DEFAULT_MODEL,
        "base_url": base_url or DEFAULT_BASE_URL,
        "timeout": timeout,
        "api_key": api_key,
    }


def get_llm_runtime_meta() -> dict[str, str]:
    """返回当前模型调用元信息，供上层记录 meta。"""
    settings = _load_runtime_settings()
    return {
        "provider": str(settings["provider"]),
        "model": str(settings["model"]),
    }


def call_llm(prompt: str) -> str:
    """调用当前配置的 LLM，并返回模型原始文本。"""
    prompt_text = str(prompt or "").strip()
    if not prompt_text:
        raise RuntimeError("prompt is empty")

    settings = _load_runtime_settings()
    if settings["provider"] != DEFAULT_PROVIDER:
        raise RuntimeError(f"unsupported provider: {settings['provider']}")
    if not settings["api_key"]:
        raise RuntimeError("missing api key for deepseek")

    payload = {
        "model": settings["model"],
        "temperature": 0,
        "messages": [
            {"role": "user", "content": prompt_text},
        ],
    }

    request = Request(
        settings["base_url"],
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {settings['api_key']}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=settings["timeout"]) as response:
            response_body = response.read().decode("utf-8")
    except HTTPError as error:
        try:
            error_body = error.read().decode("utf-8")
        except Exception:
            error_body = str(error)
        raise RuntimeError(f"llm http error {error.code}: {error_body}") from error
    except (URLError, TimeoutError) as error:
        raise RuntimeError(f"llm request failed: {error}") from error
    except Exception as error:
        raise RuntimeError(f"llm unexpected error: {error}") from error

    if not response_body.strip():
        raise RuntimeError("llm response is empty")

    try:
        response_json = json.loads(response_body)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"llm response json decode failed: {error}") from error

    try:
        content = response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise RuntimeError(f"llm response missing content: {error}") from error

    content_text = str(content or "").strip()
    if not content_text:
        raise RuntimeError("llm content is empty")

    return content_text