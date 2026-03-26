# -*- coding: utf-8 -*-
"""
modules/tag_matcher.py

第一版素材标签匹配器（可单独运行测试）

功能：
1. 读取 data/current/asset_index.json
2. 根据 section（intro / hook / explain）过滤素材池
3. 根据 tags 重合数给素材打分
4. 返回最优素材
5. 提供单文件测试入口

运行方式（推荐始终在项目根目录运行）：
    cd E:\video_agent
    python modules/tag_matcher.py

后续主链中调用方式：
    from modules.tag_matcher import match_best_asset
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple


# =========================
# 路径工具
# =========================

def get_project_root() -> str:
    """
    获取项目根目录。
    当前文件在 video_agent/modules/tag_matcher.py
    所以向上一级就是 video_agent 根目录。
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_default_asset_index_path() -> str:
    """
    默认素材索引文件路径：
    video_agent/data/current/asset_index.json
    """
    root = get_project_root()
    return os.path.join(root, "data", "current", "asset_index.json")


# =========================
# 基础加载
# =========================

def load_json(json_path: str) -> Any:
    """
    读取 JSON 文件。
    """
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"找不到 JSON 文件: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_asset_index(asset_index_path: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    读取 asset_index.json，返回素材列表。
    支持两种格式：
    1. 顶层是 list
    2. 顶层是 {"assets": [...]}
    """
    path = asset_index_path or get_default_asset_index_path()
    data = load_json(path)

    if isinstance(data, list):
        assets = data
    elif isinstance(data, dict) and "assets" in data and isinstance(data["assets"], list):
        assets = data["assets"]
    else:
        raise ValueError(
            "asset_index.json 格式不正确。应为 list，或 {'assets': [...]} 格式。"
        )

    return assets


# =========================
# 规范化工具
# =========================

def normalize_text(value: Any) -> str:
    """
    统一转成小写字符串。
    """
    if value is None:
        return ""
    return str(value).strip().lower()


def normalize_tags(tags: Any) -> List[str]:
    """
    把 tags 规范化为字符串列表。
    支持：
    - ["国债", "新闻"]
    - "国债,新闻"
    - None
    """
    if tags is None:
        return []

    if isinstance(tags, list):
        result = [normalize_text(t) for t in tags if normalize_text(t)]
        return list(dict.fromkeys(result))  # 去重并保持顺序

    if isinstance(tags, str):
        raw = tags.replace("，", ",").split(",")
        result = [normalize_text(t) for t in raw if normalize_text(t)]
        return list(dict.fromkeys(result))

    return []


def normalize_section(section: Any) -> str:
    """
    section 标准化。
    """
    return normalize_text(section)


def is_asset_enabled(asset: Dict[str, Any]) -> bool:
    """
    enabled 缺失时默认视为 True。
    """
    return bool(asset.get("enabled", True))


# =========================
# 过滤与打分
# =========================

def filter_assets_by_section(
    assets: List[Dict[str, Any]],
    section: str
) -> List[Dict[str, Any]]:
    """
    按 section 过滤素材。
    """
    section_norm = normalize_section(section)
    result: List[Dict[str, Any]] = []

    for asset in assets:
        if not is_asset_enabled(asset):
            continue

        asset_section = normalize_section(asset.get("section", ""))
        if asset_section == section_norm:
            result.append(asset)

    return result


def score_asset(scene_tags: List[str], asset_tags: List[str]) -> int:
    """
    第一版简单打分规则：
    - 标签重合一个 +1
    """
    scene_set = set(normalize_tags(scene_tags))
    asset_set = set(normalize_tags(asset_tags))
    return len(scene_set & asset_set)


def sort_assets_by_score(
    scene_tags: List[str],
    assets: List[Dict[str, Any]]
) -> List[Tuple[Dict[str, Any], int]]:
    """
    给素材打分并按分数从高到低排序。
    若分数相同，保持原始顺序。
    """
    scored: List[Tuple[Dict[str, Any], int]] = []

    for asset in assets:
        asset_tags = asset.get("tags", [])
        score = score_asset(scene_tags, asset_tags)
        scored.append((asset, score))

    scored.sort(key=lambda item: item[1], reverse=True)
    return scored


# =========================
# 默认素材 / 兜底
# =========================

def build_default_fallback_asset(section: str) -> Dict[str, Any]:
    """
    第一版兜底素材描述。
    这里只返回一个“虚拟素材描述”，后面渲染器可根据这个类型处理。
    """
    section_norm = normalize_section(section)

    return {
        "asset_id": f"{section_norm}_fallback_text_card",
        "file": "",
        "type": "text_card",
        "section": section_norm,
        "tags": [section_norm, "fallback", "text_card"],
        "enabled": True,
        "is_fallback": True,
    }


# =========================
# 对外主函数
# =========================

def match_best_asset(
    scene_tags: List[str],
    section: str,
    asset_index_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    给定 scene tags 和 section，返回一个最佳素材。
    若没有可用素材，则返回兜底素材。
    """
    all_assets = load_asset_index(asset_index_path)
    section_assets = filter_assets_by_section(all_assets, section)

    if not section_assets:
        return build_default_fallback_asset(section)

    scored_assets = sort_assets_by_score(scene_tags, section_assets)

    # 第一版规则：
    # 1) 优先选择得分最高
    # 2) 如果最高分是 0，也先返回该 section 的第一条素材
    best_asset, best_score = scored_assets[0]

    matched_asset = dict(best_asset)
    matched_asset["_match_score"] = best_score
    matched_asset["_scene_tags"] = normalize_tags(scene_tags)

    return matched_asset


def match_top_n_assets(
    scene_tags: List[str],
    section: str,
    top_n: int = 3,
    asset_index_path: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    返回前 N 个候选素材，便于以后做菜单查看或人工挑选。
    """
    all_assets = load_asset_index(asset_index_path)
    section_assets = filter_assets_by_section(all_assets, section)

    if not section_assets:
        return [build_default_fallback_asset(section)]

    scored_assets = sort_assets_by_score(scene_tags, section_assets)
    results: List[Dict[str, Any]] = []

    for asset, score in scored_assets[:top_n]:
        row = dict(asset)
        row["_match_score"] = score
        row["_scene_tags"] = normalize_tags(scene_tags)
        results.append(row)

    return results


# =========================
# 测试输出
# =========================

def print_asset(asset: Dict[str, Any], title: str = "匹配结果") -> None:
    """
    友好打印素材信息。
    """
    print("\n" + "=" * 50)
    print(title)
    print("=" * 50)
    print(f"asset_id     : {asset.get('asset_id', '')}")
    print(f"file         : {asset.get('file', '')}")
    print(f"type         : {asset.get('type', '')}")
    print(f"section      : {asset.get('section', '')}")
    print(f"tags         : {asset.get('tags', [])}")
    print(f"enabled      : {asset.get('enabled', True)}")
    print(f"is_fallback  : {asset.get('is_fallback', False)}")
    print(f"match_score  : {asset.get('_match_score', '')}")
    print(f"scene_tags   : {asset.get('_scene_tags', [])}")


def run_demo_test() -> None:
    """
    单文件演示测试。
    你可以直接运行这个 py 文件，看匹配效果。
    """
    asset_index_path = get_default_asset_index_path()

    print(f"项目根目录: {get_project_root()}")
    print(f"素材索引文件: {asset_index_path}")

    try:
        assets = load_asset_index(asset_index_path)
        print(f"\n已加载素材数量: {len(assets)}")
    except Exception as e:
        print(f"\n读取素材索引失败: {e}")
        print("请先准备 data/current/asset_index.json")
        return

    # 示例 1：新闻引子
    demo_scene_tags_1 = ["国债", "新闻", "财政"]
    demo_section_1 = "hook"
    best_asset_1 = match_best_asset(
        scene_tags=demo_scene_tags_1,
        section=demo_section_1,
        asset_index_path=asset_index_path,
    )
    print_asset(best_asset_1, title="示例1｜hook 段匹配结果")

    # 示例 2：知识解释
    demo_scene_tags_2 = ["比特币", "解释", "数字货币"]
    demo_section_2 = "explain"
    best_asset_2 = match_best_asset(
        scene_tags=demo_scene_tags_2,
        section=demo_section_2,
        asset_index_path=asset_index_path,
    )
    print_asset(best_asset_2, title="示例2｜explain 段匹配结果")

    # 示例 3：返回前3个候选
    top_assets = match_top_n_assets(
        scene_tags=["国债", "热点", "政策"],
        section="hook",
        top_n=3,
        asset_index_path=asset_index_path,
    )

    print("\n" + "=" * 50)
    print("示例3｜Top 3 候选素材")
    print("=" * 50)
    for i, asset in enumerate(top_assets, start=1):
        print(
            f"{i}. asset_id={asset.get('asset_id', '')}, "
            f"score={asset.get('_match_score', 0)}, "
            f"file={asset.get('file', '')}"
        )


if __name__ == "__main__":
    run_demo_test()