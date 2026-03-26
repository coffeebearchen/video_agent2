# -*- coding: utf-8 -*-
"""
modules/build_scene_assets.py

功能：
1. 读取 data/current/scene_plan.json
2. 调用 tag_matcher，为每个 scene 选素材
3. 生成 data/current/scene_assets.json

运行方式：
    cd E:\video_agent
    python -m modules.build_scene_assets
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from modules.tag_matcher import match_best_asset


# =========================
# 路径
# =========================

def get_project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_scene_plan_path() -> str:
    return os.path.join(get_project_root(), "data", "current", "scene_plan.json")


def get_scene_assets_path() -> str:
    return os.path.join(get_project_root(), "data", "current", "scene_assets.json")


# =========================
# JSON 工具
# =========================

def load_json(path: str) -> Any:
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到文件: {path}")

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Any, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# =========================
# scene_plan 兼容处理
# =========================

def normalize_scene_plan(scene_plan_raw: Any) -> List[Dict[str, Any]]:
    """
    兼容两种 scene_plan.json 结构：

    1）顶层直接是 list:
    [
      {...},
      {...}
    ]

    2）顶层是 dict，真正的 scenes 在 scene_plan_raw["scenes"] 里:
    {
      "title": "...",
      "scenes": [
        {...},
        {...}
      ]
    }
    """
    if isinstance(scene_plan_raw, list):
        scenes = scene_plan_raw
    elif isinstance(scene_plan_raw, dict):
        if "scenes" in scene_plan_raw and isinstance(scene_plan_raw["scenes"], list):
            scenes = scene_plan_raw["scenes"]
        else:
            raise ValueError("scene_plan.json 是 dict，但没有可用的 'scenes' 列表。")
    else:
        raise ValueError("scene_plan.json 格式不正确，必须是 list 或包含 scenes 的 dict。")

    normalized: List[Dict[str, Any]] = []
    for i, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            continue

        row = dict(scene)

        # 补 scene_id
        if "scene_id" not in row:
            row["scene_id"] = i

        # 补默认 section
        if not row.get("section"):
            row["section"] = infer_section_from_scene(row, i, len(scenes))

        # 补默认 tags
        if "tags" not in row or row.get("tags") is None:
            row["tags"] = []

        normalized.append(row)

    return normalized


def infer_section_from_scene(scene: Dict[str, Any], index: int, total: int) -> str:
    """
    如果 scene 里还没有 section，就做一个最简单推断：
    - 第1段 → intro
    - 最后一段及中间 → explain
    - 第2段 → hook

    这是为了先走通。
    """
    if total <= 1:
        return "explain"
    if index == 1:
        return "intro"
    if index == 2:
        return "hook"
    return "explain"


# =========================
# 兜底 tags
# =========================

def infer_tags_from_scene(scene: Dict[str, Any]) -> List[str]:
    """
    如果 scene 没有 tags，给一个最简单兜底：
    1. 优先用已有 tags
    2. 再尝试从 text / narration / title 里取简单词
    """
    existing_tags = scene.get("tags", [])
    if isinstance(existing_tags, list) and existing_tags:
        return existing_tags

    texts: List[str] = []
    for key in ["text", "narration", "title", "subtitle"]:
        value = scene.get(key)
        if isinstance(value, str) and value.strip():
            texts.append(value.strip())

    if not texts:
        return []

    merged = " ".join(texts)
    merged = merged.replace("，", " ").replace("。", " ").replace(",", " ").replace(".", " ")
    parts = [p.strip() for p in merged.split() if p.strip()]

    # 第一版极简：最多取前5个非空片段
    return parts[:5]


# =========================
# 核心逻辑
# =========================

def build_scene_assets_from_scenes(scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    输入：标准化后的 scenes
    输出：scene_assets 列表
    """
    results: List[Dict[str, Any]] = []

    for idx, scene in enumerate(scenes, start=1):
        section = scene.get("section", "unknown")
        tags = infer_tags_from_scene(scene)

        asset = match_best_asset(
            scene_tags=tags,
            section=section,
        )

        result = {
            "scene_id": scene.get("scene_id", idx),
            "start": scene.get("start"),
            "duration": scene.get("duration"),
            "section": section,
            "text": scene.get("text", scene.get("narration", "")),
            "tags": tags,

            # 匹配到的素材
            "asset_id": asset.get("asset_id"),
            "file": asset.get("file"),
            "type": asset.get("type"),

            # 调试信息
            "match_score": asset.get("_match_score", 0),
            "is_fallback": asset.get("is_fallback", False),
        }
        results.append(result)

    return results


# =========================
# demo 数据
# =========================

def build_demo_scene_plan() -> List[Dict[str, Any]]:
    return [
        {
            "scene_id": 1,
            "start": 0.0,
            "duration": 5.0,
            "section": "intro",
            "text": "大家好，我是……",
            "tags": ["自我介绍", "片头"]
        },
        {
            "scene_id": 2,
            "start": 5.0,
            "duration": 10.0,
            "section": "hook",
            "text": "最近很多人在讨论国债。",
            "tags": ["国债", "新闻", "财政"]
        },
        {
            "scene_id": 3,
            "start": 15.0,
            "duration": 15.0,
            "section": "explain",
            "text": "比特币可以理解成一种数字货币。",
            "tags": ["比特币", "数字货币", "解释"]
        }
    ]


# =========================
# 主流程
# =========================

def run_build() -> None:
    scene_plan_path = get_scene_plan_path()
    output_path = get_scene_assets_path()

    print(f"scene_plan 路径: {scene_plan_path}")

    if os.path.exists(scene_plan_path):
        print("使用真实 scene_plan.json")
        scene_plan_raw = load_json(scene_plan_path)
        scenes = normalize_scene_plan(scene_plan_raw)
    else:
        print("未找到 scene_plan.json → 使用 demo 测试数据")
        scenes = build_demo_scene_plan()

    scene_assets = build_scene_assets_from_scenes(scenes)

    output_data = {
        "scene_assets": scene_assets
    }
    save_json(output_data, output_path)

    print("\n生成完成：scene_assets.json")
    print("=" * 60)
    print(f"总 scene 数量: {len(scene_assets)}")
    print(f"输出文件: {output_path}")

    print("\n前 10 条 scene_assets 预览：")
    print("=" * 60)
    for s in scene_assets[:10]:
        print(
            f"scene_id={s['scene_id']} | "
            f"section={s['section']} | "
            f"asset_id={s['asset_id']} | "
            f"type={s['type']} | "
            f"score={s['match_score']} | "
            f"fallback={s['is_fallback']}"
        )


if __name__ == "__main__":
    run_build()