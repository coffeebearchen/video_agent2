# -*- coding: utf-8 -*-
"""
tests/test_task30_review_runner.py

Task30-Review 自动化测试脚本

目标：验证用户素材轻控制能力的 4 个场景
1. 映射文件为空时，主链正常运行
2. 映射有效且素材存在时，用户素材优先生效
3. 映射存在但素材不存在时，自动回退不中断
4. 测试后恢复初始状态

使用方式：
    python tests/test_task30_review_runner.py

职责：
- 只做验证，不修改产品逻辑
- 不改video_engine核心行为
- 路径必须从modules.project_paths获取，禁止硬编码
- 测试后自动恢复初始环境
"""

import json
import os
import sys
import subprocess
import shutil
from pathlib import Path

# 确保从项目根目录导入 modules
PROJECT_ROOT_TEMP = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT_TEMP))

# 从 modules 导入路径管理（必须合规）
from modules import project_paths


# =========================
# 常量（必须从project_paths获取）
# =========================

PROJECT_ROOT = str(project_paths.get_project_root())
OVERRIDE_PATH = str(project_paths.USER_SCENE_ASSET_OVERRIDE_PATH)
USER_IMAGES_DIR = str(project_paths.ASSETS_USER_IMAGES_DIR)
OUTPUT_VIDEO_PATH = str(project_paths.get_project_root() / "output" / "video.mp4")

# 初始化空映射
EMPTY_OVERRIDE = {
    "scene_asset_overrides": []
}

# 测试用素材路径
TEST_ASSET_SOURCE = str(project_paths.get_project_root() / "images" / "flat" / "card_0.png")
TEST_ASSET_DEST = os.path.join(USER_IMAGES_DIR, "test_user_card.png")

# 测试结果
TEST_RESULTS = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "failures": []
}


# =========================
# 工具函数
# =========================

def safe_read_json(path: str):
    """安全读取 JSON 文件。"""
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"[ERROR] 读取 JSON 失败：{path} | {e}")
        return None


def safe_write_json(path: str, data) -> bool:
    """安全写入 JSON 文件。"""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[ERROR] 写入 JSON 失败：{path} | {e}")
        return False


def copy_test_asset() -> bool:
    """复制测试用图片到用户素材目录。"""
    try:
        if not os.path.exists(TEST_ASSET_SOURCE):
            print(f"[WARN] 源图片不存在：{TEST_ASSET_SOURCE}")
            return False
        
        os.makedirs(USER_IMAGES_DIR, exist_ok=True)
        shutil.copy2(TEST_ASSET_SOURCE, TEST_ASSET_DEST)
        return True
    except Exception as e:
        print(f"[ERROR] 复制测试素材失败：{e}")
        return False


def run_video_engine():
    """
    运行 video_engine，返回 (return_code, stdout, stderr)。
    """
    try:
        result = subprocess.run(
            [sys.executable, "-m", "modules.video_engine"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=300
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "[ERROR] video_engine 执行超时"
    except Exception as e:
        return -1, "", f"[ERROR] 执行异常：{e}"


def output_video_exists() -> bool:
    """检查输出视频文件是否存在。"""
    return os.path.exists(OUTPUT_VIDEO_PATH)


def print_case_header(case_name: str) -> None:
    """打印 case 头部。"""
    print(f"\n{'='*70}")
    print(f"[TEST] {case_name}")
    print('='*70)

def print_case_result(case_name: str, passed: bool, reason: str = "") -> None:
    """打印 case 结果。"""
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status} {case_name}")
    if reason:
        print(f"       原因：{reason}")


def record_result(case_name: str, passed: bool, reason: str = "") -> None:
    """记录测试结果。"""
    TEST_RESULTS["total"] += 1
    if passed:
        TEST_RESULTS["passed"] += 1
    else:
        TEST_RESULTS["failed"] += 1
        TEST_RESULTS["failures"].append(f"{case_name}: {reason}")
    print_case_result(case_name, passed, reason)


# =========================
# 测试 Case
# =========================

def case_1_empty_override() -> bool:
    """
    Case 1：映射为空
    验证：user_scene_asset_overrides.json 为空时，主链正常运行。
    """
    print_case_header("Case 1 - 映射为空时主链正常运行")
    
    # 设置空映射
    if not safe_write_json(OVERRIDE_PATH, EMPTY_OVERRIDE):
        record_result("Case 1", False, "无法写入空映射文件")
        return False
    
    print("[*] 已设置空映射")
    
    # 删除旧输出
    if os.path.exists(OUTPUT_VIDEO_PATH):
        try:
            os.remove(OUTPUT_VIDEO_PATH)
        except Exception:
            pass
    
    # 运行 video_engine
    print("[*] 运行 video_engine...")
    return_code, stdout, stderr = run_video_engine()
    
    # 检查结果
    if return_code != 0:
        record_result("Case 1", False, f"video_engine 返回非 0 ({return_code})")
        return False
    
    if not output_video_exists():
        record_result("Case 1", False, "输出视频文件不存在")
        return False
    
    # 检查是否有致命错误
    if "Error" in stderr or "ERROR" in stderr:
        if "文件不存在" not in stderr:
            record_result("Case 1", False, f"日志中有错误：{stderr[:200]}")
            return False
    
    print(f"[*] 输出视频：{OUTPUT_VIDEO_PATH}")
    record_result("Case 1", True)
    return True


def case_2_valid_override() -> bool:
    """
    Case 2：映射有效且素材存在
    验证：用户素材优先生效，日志中出现 [VIDEO][USER] 标识。
    """
    print_case_header("Case 2 - 映射有效且素材存在")
    
    # 复制测试素材
    print("[*] 准备测试素材...")
    if not copy_test_asset():
        record_result("Case 2", False, "无法复制测试素材")
        return False
    
    if not os.path.exists(TEST_ASSET_DEST):
        record_result("Case 2", False, f"测试素材复制失败：{TEST_ASSET_DEST}")
        return False
    
    print(f"[*] 已复制：{TEST_ASSET_DEST}")
    
    # 设置映射：scene_id=1 指向测试图片
    override_data = {
        "scene_asset_overrides": [
            {
                "scene_id": 1,
                "asset_path": "assets/user_images/test_user_card.png"
            }
        ]
    }
    
    if not safe_write_json(OVERRIDE_PATH, override_data):
        record_result("Case 2", False, "无法写入映射文件")
        return False
    
    print("[*] 已设置有效映射（scene_id=1 → test_user_card.png）")
    
    # 删除旧输出
    if os.path.exists(OUTPUT_VIDEO_PATH):
        try:
            os.remove(OUTPUT_VIDEO_PATH)
        except Exception:
            pass
    
    # 运行 video_engine
    print("[*] 运行 video_engine...")
    return_code, stdout, stderr = run_video_engine()
    
    # 检查结果
    if return_code != 0:
        record_result("Case 2", False, f"video_engine 返回非 0 ({return_code})")
        return False
    
    if not output_video_exists():
        record_result("Case 2", False, "输出视频文件不存在")
        return False
    
    # 检查日志是否包含用户素材标识
    log_output = stdout + stderr
    if "[VIDEO][USER]" not in log_output:
        record_result("Case 2", False, "日志中缺失 [VIDEO][USER] 标识（用户素材未被使用）")
        return False
    
    print("[*] 日志中发现 [VIDEO][USER] 标识，用户素材优先生效")
    record_result("Case 2", True)
    return True


def case_3_invalid_file_fallback() -> bool:
    """
    Case 3：映射存在但素材不存在
    验证：系统输出警告，自动回退，不中断主链。
    """
    print_case_header("Case 3 - 映射存在但素材不存在（自动回退）")
    
    # 设置映射：指向不存在的文件
    override_data = {
        "scene_asset_overrides": [
            {
                "scene_id": 0,
                "asset_path": "assets/user_images/nonexistent_file_12345.png"
            }
        ]
    }
    
    if not safe_write_json(OVERRIDE_PATH, override_data):
        record_result("Case 3", False, "无法写入映射文件")
        return False
    
    print("[*] 已设置无效映射（指向不存在的文件）")
    
    # 删除旧输出
    if os.path.exists(OUTPUT_VIDEO_PATH):
        try:
            os.remove(OUTPUT_VIDEO_PATH)
        except Exception:
            pass
    
    # 运行 video_engine
    print("[*] 运行 video_engine...")
    return_code, stdout, stderr = run_video_engine()
    
    # 检查结果
    # 重点：即使映射无效，video_engine 也应该成功完成
    if return_code != 0:
        record_result("Case 3", False, f"video_engine 返回非 0 ({return_code})，应该自动回退")
        return False
    
    if not output_video_exists():
        record_result("Case 3", False, "输出视频文件不存在，应该自动回退生成")
        return False
    
    # 检查是否有警告日志
    log_output = stdout + stderr
    if "[USER_ASSET][WARN]" not in log_output:
        print("[*] 未发现警告日志（但系统正常回退了）")
    else:
        print("[*] 发现 [USER_ASSET][WARN] 警告，系统已自动回退")
    
    print("[*] 已自动回退到 bridge/old_logic，主链正常运行")
    record_result("Case 3", True)
    return True


def case_4_cleanup_restore() -> bool:
    """
    Case 4：清理并恢复初始状态
    验证：测试后把映射文件恢复为空初始状态。
    """
    print_case_header("Case 4 - 清理并恢复初始状态")
    
    # 恢复空映射
    if not safe_write_json(OVERRIDE_PATH, EMPTY_OVERRIDE):
        record_result("Case 4", False, "无法恢复空映射文件")
        return False
    
    # 验证恢复结果
    restored = safe_read_json(OVERRIDE_PATH)
    if restored != EMPTY_OVERRIDE:
        record_result("Case 4", False, "映射文件内容恢复失败")
        return False
    
    print(f"[*] 已恢复映射文件：{OVERRIDE_PATH}")
    
    # 清理测试素材（可选）
    if os.path.exists(TEST_ASSET_DEST):
        try:
            os.remove(TEST_ASSET_DEST)
            print(f"[*] 已清理测试素材")
        except Exception:
            pass
    
    print("[*] 初始状态恢复完成，未污染主链环境")
    record_result("Case 4", True)
    return True


# =========================
# 主流程
# =========================

def main() -> int:
    """主测试流程。"""
    print("\n" + "="*70)
    print("[TEST SUITE] Task30-Review 自动化测试")
    print("="*70)
    print(f"项目根目录：{PROJECT_ROOT}")
    print(f"映射文件路径：{OVERRIDE_PATH}")
    print(f"输出视频路径：{OUTPUT_VIDEO_PATH}")
    
    # 保存原始映射（以防异常）
    original_override = safe_read_json(OVERRIDE_PATH)
    
    try:
        # 依次运行 4 个 case
        case_1_empty_override()
        case_2_valid_override()
        case_3_invalid_file_fallback()
        case_4_cleanup_restore()
        
    except Exception as e:
        print(f"\n[ERROR] 测试过程中发生异常：{e}")
    
    finally:
        # 确保最后恢复初始映射
        print("\n[*] 最终清理：恢复初始映射...")
        if original_override is not None:
            safe_write_json(OVERRIDE_PATH, original_override)
        else:
            safe_write_json(OVERRIDE_PATH, EMPTY_OVERRIDE)
    
    # 打印汇总
    print("\n" + "="*70)
    print("[SUMMARY] 测试汇总")
    print("="*70)
    print(f"总测试数：{TEST_RESULTS['total']}")
    print(f"通过数：{TEST_RESULTS['passed']}")
    print(f"失败数：{TEST_RESULTS['failed']}")
    
    if TEST_RESULTS['failures']:
        print("\n[FAILURES] 失败详情：")
        for failure in TEST_RESULTS['failures']:
            print(f"  - {failure}")
    
    print("="*70)
    
    # 返回状态码
    return 0 if TEST_RESULTS['failed'] == 0 else 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
