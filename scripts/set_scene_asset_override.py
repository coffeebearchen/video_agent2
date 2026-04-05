# -*- coding: utf-8 -*-
"""
scripts/set_scene_asset_override.py

Scene 素材映射写入器

功能：
- 安全写入 user_scene_asset_overrides.json
- 支持 set (新增/更新) / remove (删除) / clear (清空) / list (查看)
- 无需手改 JSON，通过命令行管理 scene 级素材映射

使用示例：
    python scripts/set_scene_asset_override.py set --scene-id 1 --asset-path assets/user_images/intro.png
    python scripts/set_scene_asset_override.py remove --scene-id 1
    python scripts/set_scene_asset_override.py clear
    python scripts/set_scene_asset_override.py list

职责：
- 管理 user_scene_asset_overrides.json 的读写
- 保持 JSON 结构稳定
- 给出清晰的命令行反馈
- 路径统一从 modules.project_paths 获取

不负责：
- 上传文件
- 移动素材
- 生成视频
- 修改 video_engine
"""

import json
import os
import sys
import argparse
from pathlib import Path

# 从 modules 导入路径管理
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from modules import project_paths


# =========================
# 常量（全部从project_paths获取）
# =========================

PROJECT_ROOT = str(project_paths.get_project_root())
OVERRIDE_PATH = str(project_paths.USER_SCENE_ASSET_OVERRIDE_PATH)
USER_IMAGES_DIR = str(project_paths.ASSETS_USER_IMAGES_DIR)
USER_CLIPS_DIR = str(project_paths.ASSETS_USER_CLIPS_DIR)

# 初始化空结构
EMPTY_STRUCTURE = {
    "scene_asset_overrides": []
}


# =========================
# 工具函数
# =========================

def load_override_data() -> dict:
    """
    读取映射文件。
    如果不存在则自动初始化。
    """
    try:
        if os.path.exists(OVERRIDE_PATH):
            with open(OVERRIDE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 验证结构
                if isinstance(data.get("scene_asset_overrides"), list):
                    return data
                else:
                    print(f"[WARN] JSON 结构异常，将重新初始化")
                    return EMPTY_STRUCTURE.copy()
        else:
            # 文件不存在，自动初始化
            os.makedirs(os.path.dirname(OVERRIDE_PATH), exist_ok=True)
            return EMPTY_STRUCTURE.copy()
    except json.JSONDecodeError as e:
        print(f"[ERROR] JSON 损坏：{e}")
        print(f"[WARN] 将创建新的空映射文件")
        return EMPTY_STRUCTURE.copy()
    except Exception as e:
        print(f"[ERROR] 读取失败：{e}")
        return EMPTY_STRUCTURE.copy()


def save_override_data(data: dict) -> bool:
    """
    保存映射文件。
    """
    try:
        os.makedirs(os.path.dirname(OVERRIDE_PATH), exist_ok=True)
        with open(OVERRIDE_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[ERROR] 保存失败：{e}")
        return False


def normalize_override_list(items: list) -> list:
    """
    规范化映射列表（按 scene_id 升序排列）。
    """
    valid_items = [
        item for item in items
        if isinstance(item, dict) and "scene_id" in item and "asset_path" in item
    ]
    # 按 scene_id 升序排列
    return sorted(valid_items, key=lambda x: int(x["scene_id"]))


def find_override_index(items: list, scene_id: int) -> int:
    """
    查找指定 scene_id 的索引。
    不存在返回 -1。
    """
    for idx, item in enumerate(items):
        if item.get("scene_id") == scene_id:
            return idx
    return -1


def print_override_list(items: list) -> None:
    """
    美格打印映射列表。
    """
    if not items:
        print("[EMPTY] 当前无映射")
        return
    
    print(f"\n{'scene_id':<10} │ {'asset_path':<60}")
    print("-" * 75)
    for item in items:
        scene_id = item.get("scene_id", "?")
        asset_path = item.get("asset_path", "?")
        print(f"{scene_id:<10} │ {asset_path:<60}")
    print()


def asset_file_exists(asset_path: str) -> bool:
    """
    检查素材文件是否存在。
    """
    resolved = os.path.join(PROJECT_ROOT, asset_path)
    return os.path.exists(resolved)


# =========================
# 命令处理
# =========================

def cmd_set(scene_id: int, asset_path: str) -> int:
    """
    SET 命令：新增或更新映射。
    """
    # 参数验证
    if scene_id < 0:
        print(f"[ERROR] scene_id 必须为非负整数，收到：{scene_id}")
        return 1
    
    if not asset_path or not asset_path.strip():
        print(f"[ERROR] asset_path 不能为空")
        return 1
    
    asset_path = asset_path.strip()
    
    # 检查文件存在性（轻检查，只警告）
    if not asset_file_exists(asset_path):
        print(f"[WARN] 素材文件不存在：{asset_path}")
        print(f"       （系统会在运行时自动回退，允许继续）")
    
    # 读取当前数据
    data = load_override_data()
    items = data.get("scene_asset_overrides", [])
    
    # 查找是否已存在
    idx = find_override_index(items, scene_id)
    if idx >= 0:
        # 更新
        old_path = items[idx].get("asset_path", "")
        items[idx]["asset_path"] = asset_path
        print(f"\n[UPDATE] scene_id={scene_id}")
        print(f"[OLD]  {old_path}")
        print(f"[NEW]  {asset_path}\n")
    else:
        # 新增
        items.append({"scene_id": scene_id, "asset_path": asset_path})
        print(f"\n[SET] scene_id={scene_id}")
        print(f"[OK]  已写入映射：{asset_path}\n")
    
    # 规范化并保存
    data["scene_asset_overrides"] = normalize_override_list(items)
    if save_override_data(data):
        print(f"[SAVE] 映射文件已保存")
        return 0
    else:
        return 1


def cmd_remove(scene_id: int) -> int:
    """
    REMOVE 命令：删除单个映射。
    """
    if scene_id < 0:
        print(f"[ERROR] scene_id 必须为非负整数，收到：{scene_id}")
        return 1
    
    # 读取当前数据
    data = load_override_data()
    items = data.get("scene_asset_overrides", [])
    
    # 查找并删除
    idx = find_override_index(items, scene_id)
    if idx >= 0:
        removed = items.pop(idx)
        print(f"\n[REMOVE] scene_id={scene_id}")
        print(f"[OK]    已删除映射：{removed.get('asset_path', '?')}\n")
        
        # 保存
        data["scene_asset_overrides"] = normalize_override_list(items)
        if save_override_data(data):
            print(f"[SAVE]  映射文件已保存")
            return 0
        else:
            return 1
    else:
        print(f"\n[WARN] scene_id={scene_id} 不存在，无需删除\n")
        return 0


def cmd_clear() -> int:
    """
    CLEAR 命令：清空全部映射。
    """
    data = EMPTY_STRUCTURE.copy()
    print(f"\n[CLEAR] 清空全部映射")
    
    if save_override_data(data):
        print(f"[OK]    已恢复为空映射\n")
        print(f"[SAVE]  映射文件已保存")
        return 0
    else:
        return 1


def cmd_list() -> int:
    """
    LIST 命令：查看当前映射。
    """
    data = load_override_data()
    items = data.get("scene_asset_overrides", [])
    
    # 规范化排序
    items = normalize_override_list(items)
    
    print(f"\n[LIST] 当前映射（共 {len(items)} 项）")
    print(f"文件路径：{OVERRIDE_PATH}")
    print()
    
    print_override_list(items)
    
    return 0


# =========================
# 主流程
# =========================

def main():
    """主入口。"""
    parser = argparse.ArgumentParser(
        description="Scene 素材映射写入器 - 安全管理 user_scene_asset_overrides.json"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="子命令")
    
    # SET 子命令
    set_parser = subparsers.add_parser("set", help="新增或更新 scene 映射")
    set_parser.add_argument("--scene-id", type=int, required=True, help="Scene ID")
    set_parser.add_argument("--asset-path", type=str, required=True, help="素材路径（相对于项目根目录）")
    
    # REMOVE 子命令
    remove_parser = subparsers.add_parser("remove", help="删除指定 scene 映射")
    remove_parser.add_argument("--scene-id", type=int, required=True, help="Scene ID")
    
    # CLEAR 子命令
    clear_parser = subparsers.add_parser("clear", help="清空全部映射")
    
    # LIST 子命令
    list_parser = subparsers.add_parser("list", help="查看当前映射")
    
    # 解析参数
    args = parser.parse_args()
    
    # 路由到对应命令
    if args.command == "set":
        return cmd_set(args.scene_id, args.asset_path)
    elif args.command == "remove":
        return cmd_remove(args.scene_id)
    elif args.command == "clear":
        return cmd_clear()
    elif args.command == "list":
        return cmd_list()
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
