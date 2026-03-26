# -*- coding: utf-8 -*-
"""
runner/task8_resolve_assets_runner.py

【Task8：resolved_assets_plan 最小安全执行器】

作用：
1. 读取 data/current/assets_plan_v2.json
2. 扫描允许的本地素材目录 images/ 与 assets/
3. 为每个 scene 解析 primary / secondary 素材
4. 生成 data/current/resolved_assets_plan.json

边界：
- 不修改任何旧主链文件
- 不修改旧素材选择逻辑
- 仅作为外挂真实素材解析层
- 仅使用 Python 标准库
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

# 允许直接运行时找到项目根目录
CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
SCAN_DIRECTORIES = ("images", "assets")


def load_json(file_path: Path) -> Any:
    """读取 JSON 文件"""
    if not file_path.exists():
        raise FileNotFoundError(f"❌ 文件不存在：{file_path}")

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)



def save_json(file_path: Path, data: Any) -> None:
    """保存 JSON 文件"""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with file_path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)



def extract_items(data: Any) -> List[Dict[str, Any]]:
    """从 assets_plan_v2.json 中提取 items 列表"""
    if isinstance(data, dict):
        items = data.get("items")
        if isinstance(items, list):
            return items

    raise ValueError("❌ assets_plan_v2.json 中未找到有效的 items 结构")



def to_relative_path(file_path: Path) -> str:
    """转为相对项目根目录的 POSIX 路径"""
    return file_path.relative_to(PROJECT_ROOT).as_posix()



def scan_library() -> Dict[str, List[Path]]:
    """扫描允许的素材目录，仅收集支持的图片与视频文件"""
    image_files: List[Path] = []
    video_files: List[Path] = []
    flat_images: List[Path] = []

    for directory_name in SCAN_DIRECTORIES:
        root_dir = PROJECT_ROOT / directory_name
        if not root_dir.exists() or not root_dir.is_dir():
            continue

        for file_path in root_dir.rglob("*"):
            if not file_path.is_file():
                continue

            suffix = file_path.suffix.lower()
            if suffix in IMAGE_EXTENSIONS:
                image_files.append(file_path)
                if len(file_path.parts) >= 2 and file_path.parent == PROJECT_ROOT / "images" / "flat":
                    flat_images.append(file_path)
            elif suffix in VIDEO_EXTENSIONS:
                video_files.append(file_path)

    image_files.sort()
    video_files.sort()
    flat_images.sort()

    return {
        "images": image_files,
        "videos": video_files,
        "flat_images": flat_images,
    }



def choose_first(paths: Sequence[Path]) -> Optional[Path]:
    """选择列表中的第一个文件"""
    if paths:
        return paths[0]
    return None



def choose_first_excluding(paths: Sequence[Path], excluded: Optional[Path]) -> Optional[Path]:
    """选择第一个不等于 excluded 的文件，如不存在则回退为第一个"""
    for path in paths:
        if excluded is None or path != excluded:
            return path
    return choose_first(paths)



def find_card_image(scene_id: Any, flat_images: Sequence[Path]) -> Optional[Path]:
    """优先查找 images/flat/card_{scene_id}.png"""
    if scene_id is None:
        return None

    target = PROJECT_ROOT / "images" / "flat" / f"card_{scene_id}.png"
    if target in flat_images:
        return target
    return None



def resolve_text_card_only(item: Dict[str, Any], library: Dict[str, List[Path]]) -> Dict[str, Any]:
    """解析 text_card_only 模式"""
    primary = find_card_image(item.get("scene_id"), library["flat_images"])
    if primary is None:
        primary = choose_first(library["flat_images"])

    secondary = choose_first_excluding(library["images"], primary)

    if primary is None and secondary is None:
        return build_fallback_result(item)

    return build_resolved_result(item, primary, secondary)



def resolve_mixed_explain(item: Dict[str, Any], library: Dict[str, List[Path]]) -> Dict[str, Any]:
    """解析 mixed_explain 模式"""
    primary = choose_first(library["videos"])
    if primary is None:
        primary = choose_first(library["images"])

    secondary = choose_first_excluding(library["images"], primary)

    if primary is None and secondary is None:
        return build_fallback_result(item)

    return build_resolved_result(item, primary, secondary)



def resolve_summary_or_highlight(item: Dict[str, Any], library: Dict[str, List[Path]]) -> Dict[str, Any]:
    """解析 summary_card 与 highlight_card 模式"""
    primary = find_card_image(item.get("scene_id"), library["flat_images"])
    if primary is None:
        primary = choose_first(library["flat_images"])

    secondary = choose_first_excluding(library["images"], primary)

    if primary is None and secondary is None:
        return build_fallback_result(item)

    return build_resolved_result(item, primary, secondary)



def resolve_broll_bridge(item: Dict[str, Any], library: Dict[str, List[Path]]) -> Dict[str, Any]:
    """解析 broll_bridge 模式"""
    primary = choose_first(library["videos"])
    if primary is None:
        return build_fallback_result(item)

    return build_resolved_result(item, primary, None)



def resolve_default_assets(item: Dict[str, Any], library: Dict[str, List[Path]]) -> Dict[str, Any]:
    """解析 default_assets 模式"""
    primary = choose_first(library["videos"])
    if primary is None:
        primary = choose_first(library["images"])

    secondary = choose_first_excluding(library["images"], primary)

    if primary is None and secondary is None:
        return build_fallback_result(item)

    return build_resolved_result(item, primary, secondary)



def build_resolved_result(
    item: Dict[str, Any],
    primary: Optional[Path],
    secondary: Optional[Path]
) -> Dict[str, Any]:
    """构建 resolved 结果"""
    return {
        "scene_id": item.get("scene_id"),
        "role": item.get("role", ""),
        "type": item.get("type", ""),
        "asset_mode": item.get("asset_mode", ""),
        "primary_asset_type": item.get("primary_asset_type", ""),
        "secondary_asset_type": item.get("secondary_asset_type", ""),
        "primary_asset_path": to_relative_path(primary) if primary is not None else "",
        "secondary_asset_path": to_relative_path(secondary) if secondary is not None else "",
        "selection_status": "resolved",
        "fallback_reason": "",
    }



def build_fallback_result(item: Dict[str, Any]) -> Dict[str, Any]:
    """构建 fallback 结果"""
    return {
        "scene_id": item.get("scene_id"),
        "role": item.get("role", ""),
        "type": item.get("type", ""),
        "asset_mode": item.get("asset_mode", ""),
        "primary_asset_type": item.get("primary_asset_type", ""),
        "secondary_asset_type": item.get("secondary_asset_type", ""),
        "primary_asset_path": "",
        "secondary_asset_path": "",
        "selection_status": "fallback",
        "fallback_reason": "no_matching_asset_found",
    }



def resolve_item(item: Dict[str, Any], library: Dict[str, List[Path]]) -> Dict[str, Any]:
    """按 asset_mode 解析单个 scene 的素材"""
    asset_mode = item.get("asset_mode")

    if asset_mode == "text_card_only":
        return resolve_text_card_only(item, library)
    if asset_mode == "mixed_explain":
        return resolve_mixed_explain(item, library)
    if asset_mode == "summary_card":
        return resolve_summary_or_highlight(item, library)
    if asset_mode == "highlight_card":
        return resolve_summary_or_highlight(item, library)
    if asset_mode == "broll_bridge":
        return resolve_broll_bridge(item, library)

    return resolve_default_assets(item, library)



def build_resolved_items(items: List[Dict[str, Any]], library: Dict[str, List[Path]]) -> List[Dict[str, Any]]:
    """批量解析素材"""
    return [resolve_item(item, library) for item in items]



def main() -> None:
    """主执行入口"""
    input_file = PROJECT_ROOT / "data" / "current" / "assets_plan_v2.json"
    output_file = PROJECT_ROOT / "data" / "current" / "resolved_assets_plan.json"

    print("=" * 60)
    print("开始执行 Task8：生成 resolved_assets_plan.json")
    print("=" * 60)
    print(f"输入文件：{input_file}")
    print(f"输出文件：{output_file}")

    input_data = load_json(input_file)
    items = extract_items(input_data)
    library = scan_library()
    resolved_items = build_resolved_items(items, library)

    output_data = {
        "source_file": "data/current/assets_plan_v2.json",
        "output_file": "data/current/resolved_assets_plan.json",
        "scene_count": len(items),
        "library_summary": {
            "image_count": len(library["images"]),
            "video_count": len(library["videos"]),
        },
        "items": resolved_items,
    }

    save_json(output_file, output_data)

    print("✅ resolved_assets_plan.json 已生成")
    print(f"输出路径：{output_file}")
    print(f"图片数量：{len(library['images'])}")
    print(f"视频数量：{len(library['videos'])}")
    print("=" * 60)


if __name__ == "__main__":
    main()
