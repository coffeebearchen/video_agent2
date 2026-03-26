# -*- coding: utf-8 -*-
"""
文件名：config_loader.py
作用说明：
1. 统一从 project_paths 获取 config.json 路径
2. 提供最小默认配置与递归兜底
3. 清洗并归一化配置字段
4. 返回统一可直接使用的运行时配置和日志

设计边界：
1. 只处理 Task30 允许的 3 类配置项
2. 不扩展为新的主链控制总线
3. 不在这里写 scene 逻辑和渲染逻辑
"""

from __future__ import annotations

import os
import json
from copy import deepcopy
from types import SimpleNamespace

from modules import project_paths


DEFAULT_STYLE_PRESET = "serious"
ALLOWED_STYLE_PRESETS = {"serious", "fast", "story"}
DEFAULT_MAX_PER_SCENE = 2
MIN_MAX_PER_SCENE = 1
MAX_MAX_PER_SCENE = 2


def get_default_config():
    """返回 Task30 允许的最小默认配置。"""
    return {
        "auto_directives": {
            "enabled": True,
        },
        "style": {
            "preset": DEFAULT_STYLE_PRESET,
        },
        "insert_policy": {
            "max_per_scene": DEFAULT_MAX_PER_SCENE,
        },
    }


def get_project_paths():
    """兼容获取项目路径对象，优先复用 project_paths 模块能力。"""
    if hasattr(project_paths, "get_project_paths"):
        return project_paths.get_project_paths()

    config_path = getattr(
        project_paths,
        "CONFIG_JSON_PATH",
        project_paths.get_project_root() / "config.json",
    )
    return SimpleNamespace(CONFIG_JSON=config_path)


def get_config_path(config_path=None):
    """统一解析 config.json 路径。"""
    if config_path:
        return config_path

    paths = get_project_paths()
    return getattr(paths, "CONFIG_JSON", project_paths.get_project_root() / "config.json")


def merge_config(user_config, default_config):
    """递归合并用户配置与默认配置。"""
    merged = deepcopy(user_config) if isinstance(user_config, dict) else {}

    for key, default_value in default_config.items():
        if key not in merged:
            merged[key] = deepcopy(default_value)
        elif isinstance(default_value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_config(merged[key], default_value)

    return merged


def get_config_value(config, path, default=None):
    """安全获取配置值，避免多层 get 隐式扩散。"""
    current_value = config
    for key in path:
        if not isinstance(current_value, dict) or key not in current_value:
            return default
        current_value = current_value[key]

    return current_value


def _normalize_bool(value, default_value):
    """将常见布尔输入收敛为 bool。"""
    if isinstance(value, bool):
        return value, False

    if isinstance(value, int) and value in (0, 1):
        return bool(value), False

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes", "on"}:
            return True, False
        if normalized in {"false", "0", "no", "off"}:
            return False, False

    return default_value, True


def _normalize_style_preset(value):
    """将 style preset 收敛为 serious / fast / story。"""
    normalized = str(value or "").strip().lower()
    if normalized in ALLOWED_STYLE_PRESETS:
        return normalized, False

    return DEFAULT_STYLE_PRESET, True


def _normalize_max_per_scene(value):
    """将 max_per_scene 限制在 1~2。"""
    normalized = None

    if isinstance(value, bool):
        normalized = None
    elif isinstance(value, int):
        normalized = value
    elif isinstance(value, str):
        stripped = value.strip()
        if stripped.isdigit():
            normalized = int(stripped)

    if normalized is None:
        return DEFAULT_MAX_PER_SCENE, True

    if normalized < MIN_MAX_PER_SCENE or normalized > MAX_MAX_PER_SCENE:
        return DEFAULT_MAX_PER_SCENE, True

    return normalized, False


def load_config_file(config_path):
    """读取 config.json；文件缺失或解析失败时返回空数据和日志。"""
    resolved_path = get_config_path(config_path)
    logs = []

    logs.append(f"配置路径来源：project_paths -> {resolved_path}")

    if not os.path.exists(resolved_path):
        logs.append(f"未找到 config.json，已使用默认配置：{resolved_path}")
        return {
            "data": {},
            "logs": logs,
            "file_exists": False,
            "config_path": str(resolved_path),
        }

    try:
        with open(resolved_path, "r", encoding="utf-8") as file:
            raw_data = json.load(file)
    except Exception as error:
        logs.append(f"config.json 读取失败，已使用默认配置：{resolved_path}")
        logs.append(f"读取失败原因：{error}")
        return {
            "data": {},
            "logs": logs,
            "file_exists": True,
            "config_path": str(resolved_path),
        }

    if not isinstance(raw_data, dict):
        logs.append(f"config.json 根结构非法，已使用默认配置：{resolved_path}")
        return {
            "data": {},
            "logs": logs,
            "file_exists": True,
            "config_path": str(resolved_path),
        }

    logs.append(f"已读取 config.json：{resolved_path}")
    return {
        "data": raw_data,
        "logs": logs,
        "file_exists": True,
        "config_path": str(resolved_path),
    }


def normalize_config(config_data):
    """对配置字段进行清洗、范围限制和来源标记。"""
    raw_data = config_data if isinstance(config_data, dict) else {}
    normalized_config = merge_config(raw_data, get_default_config())
    default_config = get_default_config()
    logs = []
    provided = {
        "auto_directives.enabled": False,
        "style.preset": False,
        "insert_policy.max_per_scene": False,
    }

    auto_config = get_config_value(raw_data, ["auto_directives"], {})
    if isinstance(auto_config, dict) and "enabled" in auto_config:
        provided["auto_directives.enabled"] = True
        enabled_value, used_default = _normalize_bool(
            get_config_value(auto_config, ["enabled"]),
            default_value=get_config_value(default_config, ["auto_directives", "enabled"]),
        )
        normalized_config["auto_directives"]["enabled"] = enabled_value
        if used_default:
            logs.append("auto_directives.enabled 非法，已回退 true")

    style_config = get_config_value(raw_data, ["style"], {})
    if isinstance(style_config, dict) and "preset" in style_config:
        provided["style.preset"] = True
        preset_value, used_default = _normalize_style_preset(
            get_config_value(style_config, ["preset"])
        )
        normalized_config["style"]["preset"] = preset_value
        if used_default:
            logs.append(f"style.preset 非法，已回退 {DEFAULT_STYLE_PRESET}")

    insert_policy_config = get_config_value(raw_data, ["insert_policy"], {})
    if isinstance(insert_policy_config, dict) and "max_per_scene" in insert_policy_config:
        provided["insert_policy.max_per_scene"] = True
        max_per_scene, used_default = _normalize_max_per_scene(
            get_config_value(insert_policy_config, ["max_per_scene"])
        )
        normalized_config["insert_policy"]["max_per_scene"] = max_per_scene
        if used_default:
            logs.append(
                f"insert_policy.max_per_scene 非法，已回退 {DEFAULT_MAX_PER_SCENE}"
            )

    logs.append(
        f"auto_directives.enabled = "
        f"{str(get_config_value(normalized_config, ['auto_directives', 'enabled'])).lower()}"
    )
    logs.append(
        f"insert_policy.max_per_scene = "
        f"{get_config_value(normalized_config, ['insert_policy', 'max_per_scene'])}"
    )
    logs.append(
        f"style preset 来源：config.json -> "
        f"{get_config_value(normalized_config, ['style', 'preset'])}"
    )

    return {
        "config": normalized_config,
        "logs": logs,
        "meta": {
            "provided": provided,
        },
    }


def load_runtime_config(config_path=None):
    """统一返回可直接使用的配置、日志和来源元信息。"""
    file_result = load_config_file(config_path)
    normalized_result = normalize_config(file_result.get("data", {}))

    return {
        "config": normalized_result["config"],
        "logs": file_result.get("logs", []) + normalized_result.get("logs", []),
        "meta": {
            "config_path": file_result.get("config_path", str(get_config_path(config_path))),
            "file_exists": file_result.get("file_exists", False),
            "provided": normalized_result.get("meta", {}).get("provided", {}),
        },
    }


def load_config(config_path=None):
    """兼容返回纯配置字典，供轻量调用场景复用。"""
    return load_runtime_config(config_path).get("config", get_default_config())