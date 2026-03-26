# -*- coding: utf-8 -*-
"""
asset_selector.py

【素材选择模块｜实用化升级版】

职责：
1. 从多个来源选择素材：asset_index、分类目录、inserts/clips、fallback
2. 支持 image 和 video 两种素材类型
3. 准确标记 fallback 和计算 match_score
4. 所有路径统一来自 project_paths
5. 提供可调试日志
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict, List, Optional

from modules import project_paths
from modules.asset_registry import DEFAULT_INSERT_PATH


# ===== 关键词分类映射 =====
KEYWORD_CATEGORIES = {
    "finance": {
        "keywords": [
            "比特币", "货币", "债券", "金融", "上涨", "下跌", "突破", "震荡",
            "新高", "回调", "行情", "走势", "资金", "流入", "流出", "买入",
            "抛售", "增持", "减持", "仓位", "美联储", "加息", "降息", "利率",
            "通胀", "预期", "政策", "ETF", "现货ETF", "股票", "市场", 
            "投资者", "风险资产", "通货膨胀"
        ],
        "dir": "assets/library/finance"
    },
    "tech": {
        "keywords": [
            "科技", "AI", "人工智能", "软件", "应用", "平台", "手机", 
            "工具", "模型", "算法", "开发", "代码", "编程", "技术"
        ],
        "dir": "assets/library/tech"
    },
}


def get_project_paths():
    """兼容获取路径对象，统一从 project_paths 模块派生。"""
    if hasattr(project_paths, "get_project_paths"):
        return project_paths.get_project_paths()

    asset_index_path = getattr(
        project_paths,
        "ASSET_INDEX_JSON",
        getattr(project_paths, "ASSET_INDEX_PATH", project_paths.get_asset_index_path()),
    )
    assets_dir = getattr(
        project_paths,
        "ASSETS_DIR",
        project_paths.get_assets_dir(),
    )
    default_asset = getattr(
        project_paths,
        "DEFAULT_ASSET",
        project_paths.ASSETS_INSERTS_DIR / Path(DEFAULT_INSERT_PATH).name,
    )
    return SimpleNamespace(
        ASSET_INDEX_JSON=asset_index_path,
        ASSETS_DIR=assets_dir,
        DEFAULT_ASSET=default_asset,
    )


def _normalize_asset_index_data(data):
    """兼容 list / dict 两种 asset_index 结构。"""
    if isinstance(data, list):
        return data

    if isinstance(data, dict):
        assets = data.get("assets", [])
        if isinstance(assets, list):
            return assets

    return []


def load_asset_index():
    """安全读取 asset_index.json。"""
    paths = get_project_paths()
    asset_index_path = getattr(paths, "ASSET_INDEX_JSON", None)

    if not asset_index_path or not os.path.exists(asset_index_path):
        return []

    try:
        with open(asset_index_path, "r", encoding="utf-8") as file:
            data = json.load(file)
    except Exception as error:
        print(f"[ASSET][ERROR] 读取 asset_index.json 失败：{error}")
        return []

    assets = _normalize_asset_index_data(data)
    if not isinstance(assets, list):
        return []

    return assets


def get_fallback_asset():
    """获取 fallback 素材路径。"""
    paths = get_project_paths()
    fallback_path = getattr(paths, "DEFAULT_ASSET", None)

    if fallback_path and os.path.exists(fallback_path):
        return str(Path(fallback_path).resolve())

    return None


def _get_asset_type(file_path: str) -> str:
    """根据文件后缀判断素材类型。"""
    if not file_path:
        return "image"
    
    ext = Path(file_path).suffix.lower()
    if ext in [".mp4", ".mov", ".avi", ".webm", ".mkv"]:
        return "video"
    
    return "image"


def _scan_directory_for_assets(directory_path: str) -> List[str]:
    """扫描目录中的所有素材文件。"""
    assets = []
    
    if not os.path.isdir(directory_path):
        return assets
    
    image_exts = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
    video_exts = {".mp4", ".mov", ".avi", ".webm", ".mkv"}
    
    for item in os.listdir(directory_path):
        item_path = os.path.join(directory_path, item)
        if os.path.isfile(item_path):
            item_ext = Path(item).suffix.lower()
            if item_ext in image_exts or item_ext in video_exts:
                assets.append(str(Path(item_path).resolve()))
    
    return sorted(assets)


def _match_keyword_and_get_category(text: str) -> tuple[Optional[str], Optional[str]]:
    """
    匹配文本关键词，返回 (匹配的关键词, 对应的分类目录)
    """
    text_lower = str(text or "").strip().lower()
    
    for category_name, category_info in KEYWORD_CATEGORIES.items():
        keywords = category_info.get("keywords", [])
        for keyword in keywords:
            if keyword.lower() in text_lower:
                return (keyword, category_name)
    
    return (None, None)


def select_asset_from_index(text: str) -> Optional[Dict[str, Any]]:
    """从 asset_index 中选择素材。"""
    assets = load_asset_index()
    
    if not assets:
        return None
    
    text_lower = str(text or "").strip().lower()
    
    # 尝试从 asset_index 中匹配
    for item in assets:
        if not isinstance(item, dict):
            continue
        
        # 检查 tags
        tags = item.get("tags", [])
        if isinstance(tags, list):
            for tag in tags:
                if str(tag or "").strip().lower() in text_lower:
                    asset_path = item.get("path")
                    if asset_path:
                        full_path = project_paths.get_project_root() / asset_path
                        if os.path.exists(full_path):
                            return {
                                "file": str(full_path.resolve()),
                                "keyword": str(tag),
                                "score": 100,
                                "source": "asset_index_tag"
                            }
        
        # 检查文件名等字段
        for field in ["file_name", "path", "category"]:
            field_value = str(item.get(field, "")).lower()
            if text_lower and text_lower in field_value:
                asset_path = item.get("path")
                if asset_path:
                    full_path = project_paths.get_project_root() / asset_path
                    if os.path.exists(full_path):
                        return {
                            "file": str(full_path.resolve()),
                            "keyword": text_lower[:20],
                            "score": 60,
                            "source": "asset_index_field"
                        }
    
    return None


def select_asset_from_categories(text: str) -> Optional[Dict[str, Any]]:
    """从分类目录（finance/tech）中选择素材。"""
    matched_keyword, category_name = _match_keyword_and_get_category(text)
    
    if not matched_keyword or not category_name:
        return None
    
    category_info = KEYWORD_CATEGORIES.get(category_name, {})
    category_dir = category_info.get("dir", "")
    
    if not category_dir:
        return None
    
    full_dir_path = str(project_paths.get_project_root() / category_dir)
    
    if not os.path.isdir(full_dir_path):
        return None
    
    # 扫描目录中的所有素材
    available_assets = _scan_directory_for_assets(full_dir_path)
    
    if available_assets:
        selected_asset = random.choice(available_assets)
        return {
            "file": selected_asset,
            "keyword": matched_keyword,
            "score": 80,
            "source": "category_directory"
        }
    
    return None


def select_asset_from_inserts_clips() -> Optional[Dict[str, Any]]:
    """从 inserts / clips 目录中直接选择素材。"""
    inserts_dir = str(project_paths.ASSETS_INSERTS_DIR)
    
    if os.path.isdir(inserts_dir):
        assets = _scan_directory_for_assets(inserts_dir)
        # 排除 default.png
        assets = [a for a in assets if not a.endswith("default.png")]
        
        if assets:
            selected_asset = random.choice(assets)
            return {
                "file": selected_asset,
                "keyword": "",
                "score": 40,
                "source": "inserts_directory"
            }
    
    return None


def _build_success_result(
    text: str,
    matched_keyword: str,
    asset_file: str,
    match_score: int,
    source: str
) -> Dict[str, Any]:
    """构建成功匹配的返回结果。"""
    asset_type = _get_asset_type(asset_file)
    
    return {
        "matched": True,
        "asset_type": asset_type,
        "asset_file": asset_file,
        "keyword": matched_keyword,
        "reason": f"从{source}中匹配到素材",
        "match_score": match_score,
        "is_fallback": False,
        "matched_keyword": matched_keyword,
    }


def _build_fallback_result(text: str) -> Dict[str, Any]:
    """构建 fallback 的返回结果。"""
    fallback_file = get_fallback_asset()
    
    if not fallback_file:
        return {
            "matched": False,
            "asset_type": "text_card",
            "asset_file": "",
            "keyword": "",
            "reason": "无可用素材，使用 text_card fallback",
            "match_score": 0,
            "is_fallback": True,
            "matched_keyword": "",
        }
    
    asset_type = _get_asset_type(fallback_file)
    
    return {
        "matched": asset_type == "image",
        "asset_type": asset_type,
        "asset_file": fallback_file,
        "keyword": "",
        "reason": "未命中有效素材，使用默认素材",
        "match_score": 0,
        "is_fallback": True,
        "matched_keyword": "",
    }


def select_asset_for_text(text: str) -> Dict[str, Any]:
    """
    根据文本选择素材。
    
    优先级：
    1. asset_index 精确标签命中
    2. 分类目录关键词命中
    3. inserts/clips 目录直接选择
    4. fallback
    """
    print(f"[ASSET] 查询文本：{text}")
    
    # 优先从 asset_index 选
    result = select_asset_from_index(text)
    if result:
        print(f"[ASSET] 命中关键词：{result['keyword']}")
        print(f"[ASSET] 命中素材类型：{_get_asset_type(result['file'])}")
        print(f"[ASSET] 命中素材路径：{result['file']}")
        print(f"[ASSET] match_score：{result['score']}")
        print("[ASSET] fallback：false")
        return _build_success_result(
            text,
            result["keyword"],
            result["file"],
            result["score"],
            "asset_index"
        )
    
    # 从分类目录选
    result = select_asset_from_categories(text)
    if result:
        print(f"[ASSET] 命中关键词：{result['keyword']}")
        print(f"[ASSET] 命中素材类型：{_get_asset_type(result['file'])}")
        print(f"[ASSET] 命中素材路径：{result['file']}")
        print(f"[ASSET] match_score：{result['score']}")
        print("[ASSET] fallback：false")
        return _build_success_result(
            text,
            result["keyword"],
            result["file"],
            result["score"],
            "category"
        )
    
    # 从 inserts/clips 选
    result = select_asset_from_inserts_clips()
    if result:
        print(f"[ASSET] 命中素材类型：{_get_asset_type(result['file'])}")
        print(f"[ASSET] 命中素材路径：{result['file']}")
        print(f"[ASSET] match_score：{result['score']}")
        print("[ASSET] fallback：false")
        return _build_success_result(
            text,
            result["keyword"],
            result["file"],
            result["score"],
            "inserts"
        )
    
    # fallback
    print("[ASSET][WARN] 未命中有效素材，使用 fallback")
    print("[ASSET] fallback：true")
    return _build_fallback_result(text)