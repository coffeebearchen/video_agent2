import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.json"
API_CONFIG_PATH = Path(__file__).resolve().parent.parent / "api_config.json"
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"
DEFAULT_PROVIDER = "deepseek"
DEFAULT_TIMEOUT = 5
RESPONSE_PREVIEW_LIMIT = 400


def _load_json_file(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _truncate_text(text: str, limit: int = RESPONSE_PREVIEW_LIMIT) -> str:
    normalized = str(text or "").strip()
    if len(normalized) <= limit:
        return normalized
    return normalized[:limit] + "..."


def _load_runtime_settings() -> Dict[str, Any]:
    config = _load_json_file(CONFIG_PATH)
    api_config = _load_json_file(API_CONFIG_PATH)
    ai_config = config.get("ai_candidate", {}) if isinstance(config, dict) else {}

    provider = str(ai_config.get("provider") or api_config.get("provider") or os.getenv("DEEPSEEK_PROVIDER") or DEFAULT_PROVIDER).strip()
    provider_source = "config.json" if ai_config.get("provider") else (
        "api_config.json" if api_config.get("provider") else (
            "environment" if os.getenv("DEEPSEEK_PROVIDER") else "hardcoded"
        )
    )

    base_url = str(
        ai_config.get("base_url")
        or api_config.get("base_url")
        or os.getenv("DEEPSEEK_BASE_URL")
        or DEEPSEEK_URL
    ).strip()
    base_url_source = "config.json" if ai_config.get("base_url") else (
        "api_config.json" if api_config.get("base_url") else (
            "environment" if os.getenv("DEEPSEEK_BASE_URL") else "hardcoded"
        )
    )

    timeout_value = ai_config.get("timeout")
    if timeout_value is None:
        timeout_value = api_config.get("timeout")
    if timeout_value is None:
        timeout_value = os.getenv("DEEPSEEK_TIMEOUT")
    timeout_source = "config.json" if ai_config.get("timeout") is not None else (
        "api_config.json" if api_config.get("timeout") is not None else (
            "environment" if os.getenv("DEEPSEEK_TIMEOUT") else "hardcoded"
        )
    )
    try:
        timeout = max(1, int(timeout_value if timeout_value is not None else DEFAULT_TIMEOUT))
    except Exception:
        timeout = DEFAULT_TIMEOUT

    config_api_key = str(ai_config.get("api_key", "")).strip()
    api_config_key = str(api_config.get("api_key", "")).strip()
    env_api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if config_api_key:
        api_key = config_api_key
        api_key_source = "config.json"
    elif api_config_key:
        api_key = api_config_key
        api_key_source = "api_config.json"
    elif env_api_key:
        api_key = env_api_key
        api_key_source = "environment"
    else:
        api_key = ""
        api_key_source = "missing"

    return {
        "provider": provider or DEFAULT_PROVIDER,
        "provider_source": provider_source,
        "base_url": base_url,
        "base_url_source": base_url_source,
        "timeout": timeout,
        "timeout_source": timeout_source,
        "api_key": api_key,
        "api_key_source": api_key_source,
        "api_key_present": bool(api_key),
    }


def _build_prompt(raw_text: str) -> str:
    return (
        "请基于以下内容生成：\n\n"
        "1）3个适合视频封面的短标题（6~12字，完整句）\n"
        "2）3个用于强调的短语（4~12字，突出记忆点）\n\n"
        f"内容：\n{raw_text}\n\n"
        "要求：\n"
        "- 中文\n"
        "- 不要解释\n"
        "- 只输出 JSON：\n"
        "{\n"
        '  "title_candidates": ["...", "...", "..."],\n'
        '  "highlight_candidates": ["...", "...", "..."]\n'
        "}"
    )


def _extract_json_text(content: str) -> Optional[str]:
    text = str(content or "").strip()
    if not text:
        return None

    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    return text[start:end + 1]


def _sanitize_candidate_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []

    result: List[str] = []
    for item in value:
        text = str(item or "").strip()
        if text:
            result.append(text)
        if len(result) >= 3:
            break

    return result


def _parse_candidate_payload(payload: Dict[str, Any]) -> Optional[Dict[str, List[str]]]:
    title_candidates = _sanitize_candidate_list(payload.get("title_candidates") or payload.get("titles"))
    highlight_candidates = _sanitize_candidate_list(payload.get("highlight_candidates") or payload.get("highlights"))

    if not title_candidates or not highlight_candidates:
        return None

    return {
        "title_candidates": title_candidates,
        "highlight_candidates": highlight_candidates,
    }


def get_deepseek_runtime_status() -> Dict[str, Any]:
    settings = _load_runtime_settings()
    return {
        "provider": settings["provider"],
        "provider_source": settings["provider_source"],
        "base_url": settings["base_url"],
        "base_url_source": settings["base_url_source"],
        "api_key_present": settings["api_key_present"],
        "api_key_source": settings["api_key_source"],
        "timeout": settings["timeout"],
        "timeout_source": settings["timeout_source"],
    }


def diagnose_ai_candidates(raw_text: str) -> Dict[str, Any]:
    settings = _load_runtime_settings()
    result: Dict[str, Any] = {
        "ok": False,
        "stage": "request_failed",
        "message": "unknown error",
        "provider": settings["provider"],
        "provider_source": settings["provider_source"],
        "base_url": settings["base_url"],
        "base_url_source": settings["base_url_source"],
        "api_key_present": settings["api_key_present"],
        "api_key_source": settings["api_key_source"],
        "timeout": settings["timeout"],
        "timeout_source": settings["timeout_source"],
        "request_sent": False,
        "status_code": None,
        "response_preview": "",
        "raw_text": _truncate_text(raw_text, limit=120),
        "candidates": None,
    }

    if settings["provider"] != DEFAULT_PROVIDER:
        result["stage"] = "request_failed"
        result["message"] = f"unsupported provider: {settings['provider']}"
        return result

    if not settings["base_url"]:
        result["stage"] = "missing_base_url"
        result["message"] = "base_url is empty"
        return result

    if not settings["api_key_present"]:
        result["stage"] = "missing_api_key"
        result["message"] = "no DeepSeek API key found in config.json, api_config.json, or environment"
        return result

    payload = {
        "model": "deepseek-chat",
        "temperature": 0,
        "messages": [
            {"role": "user", "content": _build_prompt(raw_text)},
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
        result["request_sent"] = True
        with urlopen(request, timeout=settings["timeout"]) as response:
            result["status_code"] = getattr(response, "status", None) or response.getcode()
            response_body = response.read().decode("utf-8")
    except HTTPError as error:
        result["request_sent"] = True
        result["status_code"] = getattr(error, "code", None)
        try:
            error_body = error.read().decode("utf-8")
        except Exception:
            error_body = str(error)
        result["response_preview"] = _truncate_text(error_body)
        result["stage"] = "bad_status_code"
        result["message"] = f"HTTP {result['status_code']}"
        return result
    except (URLError, TimeoutError) as error:
        result["request_sent"] = True
        result["stage"] = "request_failed"
        result["message"] = str(error)
        return result
    except Exception as error:
        result["request_sent"] = True
        result["stage"] = "request_failed"
        result["message"] = str(error)
        return result

    if not response_body.strip():
        result["stage"] = "empty_response"
        result["message"] = "empty response body"
        return result

    result["response_preview"] = _truncate_text(response_body)

    try:
        response_json = json.loads(response_body)
    except json.JSONDecodeError as error:
        result["stage"] = "json_parse_failed"
        result["message"] = f"response JSON decode failed: {error}"
        return result

    try:
        content = response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        result["stage"] = "empty_response"
        result["message"] = f"missing choices/message/content: {error}"
        result["response_preview"] = _truncate_text(json.dumps(response_json, ensure_ascii=False))
        return result

    if not str(content or "").strip():
        result["stage"] = "empty_response"
        result["message"] = "model returned empty content"
        return result

    result["response_preview"] = _truncate_text(content)
    json_text = _extract_json_text(content)
    if not json_text:
        result["stage"] = "json_parse_failed"
        result["message"] = "no JSON object found in model content"
        return result

    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError as error:
        result["stage"] = "json_parse_failed"
        result["message"] = f"model content JSON decode failed: {error}"
        result["response_preview"] = _truncate_text(json_text)
        return result

    candidates = _parse_candidate_payload(parsed)
    if candidates is None:
        result["stage"] = "invalid_candidate_shape"
        result["message"] = "candidate payload missing title/highlight arrays"
        result["response_preview"] = _truncate_text(json.dumps(parsed, ensure_ascii=False))
        return result

    result["ok"] = True
    result["stage"] = "success"
    result["message"] = "DeepSeek candidates generated successfully"
    result["candidates"] = candidates
    return result


def generate_ai_candidates(raw_text: str) -> Optional[Dict[str, List[str]]]:
    diagnostic = diagnose_ai_candidates(raw_text)
    return diagnostic.get("candidates") if diagnostic.get("ok") else None