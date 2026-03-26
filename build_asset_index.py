# -*- coding: utf-8 -*-
"""
文件名：build_asset_index.py
作用说明：
1. 独立运行标准素材索引生成
2. 自动创建固定素材目录
3. 输出清晰中文日志
"""

from __future__ import annotations

from modules.asset_registry import DEFAULT_INSERT_NOTE, build_asset_index


def main():
    print("=" * 60)
    print("开始生成标准素材索引...")
    print("=" * 60)

    result = build_asset_index()

    for log_line in result.get("logs", []):
        print(f"[AssetRegistry] {log_line}")

    index_data = result.get("index", {})
    summary = result.get("summary", {})
    assets = index_data.get("assets", [])

    for category, category_summary in summary.items():
        print(
            f"[AssetRegistry] {category}："
            f"已收录 {category_summary.get('count', 0)} 项，"
            f"忽略 {category_summary.get('ignored', 0)} 项"
        )

    default_insert_path = "assets/inserts/default.png"
    if any(asset.get("path") == default_insert_path for asset in assets):
        print(f"[AssetRegistry] 检测到默认插图入口：{default_insert_path}")
        print(f"[AssetRegistry] 说明：{DEFAULT_INSERT_NOTE}")

    print(f"[AssetRegistry] 素材总数：{len(assets)}")
    print(f"[AssetRegistry] 已生成素材索引：{result.get('output_path')}")
    print("=" * 60)


if __name__ == "__main__":
    main()