# -*- coding: utf-8 -*-
"""
tests/test_scene_count_control_runner.py

Task33 - Scene Count 控制能力测试套件

目标：验证 scene_count 参数的三种工作模式：
1. 默认模式（不传 scene_count）→ 自动逻辑，保持 3 个 scene
2. 显式指定 3 → 生成 3 个 scene
3. 显式指定 5 → 生成 5 个 scene

验证内容：
- scene_plan.json 中的 scene 数量正确
- 视频正常生成
- 日志输出包含 [SCENE_COUNT] 标记
"""

import json
import os
import sys
import io
import subprocess
import re
from pathlib import Path

# 设置stdout为UTF-8编码
if (sys.stdout.encoding or "").lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

SUBPROCESS_ENV = os.environ.copy()
SUBPROCESS_ENV["PYTHONIOENCODING"] = "utf-8"
SUBPROCESS_ENV["PYTHONUTF8"] = "1"

from modules import project_paths
import run_pipeline_user

SCENE_PLAN_CURRENT = project_paths.get_data_current_dir() / "scene_plan.json"
SCENE_PLAN_ROOT = PROJECT_ROOT / "scene_plan.json"
OUTPUT_VIDEO_PATH = project_paths.get_project_root() / "output" / "video.mp4"
INPUT_JSON_PATH = PROJECT_ROOT / "input.json"
AUDIO_DIR = project_paths.get_project_root() / "audio"


def extract_metric(text: str, metric_name: str) -> int:
    match = re.search(rf"\[{re.escape('SCENE_SPLIT')}\] {re.escape(metric_name)}=(\d+)", text or "")
    if not match:
        return -1
    return int(match.group(1))


def safe_read_json(path: Path):
    """安全读取JSON文件。"""
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None
    except Exception as e:
        print(f"[ERROR] 读取 JSON 失败：{path} | {e}")
        return None


def safe_write_json(path: Path, data) -> bool:
    """安全写入JSON文件。"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"[ERROR] 写入 JSON 失败：{path} | {e}")
        return False


def read_scene_plan() -> int:
    """读取 scene_plan.json，返回场景数量。"""
    data = safe_read_json(SCENE_PLAN_CURRENT)
    if data is None:
        data = safe_read_json(SCENE_PLAN_ROOT)
    
    if data is None:
        return 0
    
    # 处理两种格式：直接list 或 {"scenes": [...]}
    if isinstance(data, list):
        return len(data)
    elif isinstance(data, dict):
        scenes = data.get("scenes", [])
        if isinstance(scenes, list):
            return len(scenes)
    
    return 0


def cleanup_old_output():
    """清理旧输出文件。"""
    if OUTPUT_VIDEO_PATH.exists():
        try:
            OUTPUT_VIDEO_PATH.unlink()
        except Exception:
            pass

    if AUDIO_DIR.exists():
        for path in AUDIO_DIR.glob("card_*.mp3"):
            try:
                path.unlink()
            except Exception:
                pass


def prepare_input_json():
    """准备输入JSON文件（简单文本）。"""
    input_data = {
        "type": "text",
        "content": "这是一个测试文本。\n用来验证scene_count的控制能力。\n系统应该按照指定的scene数量生成。"
    }
    return safe_write_json(INPUT_JSON_PATH, input_data)


def count_generated_audio_files() -> int:
    if not AUDIO_DIR.exists():
        return 0
    return len(list(AUDIO_DIR.glob("card_*.mp3")))


def count_missing_audio_files(final_scene_count: int) -> int:
    missing = 0
    for index in range(final_scene_count):
        if not (AUDIO_DIR / f"card_{index}.mp3").exists():
            missing += 1
    return missing


def run_pipeline_by_scene_count(scene_count):
    """
    运行完整的视频生成流程，指定 scene_count。

    真实运行完整主链，检查 scene/audio/video 的完整性。
    返回结果字典。
    """
    print(f"\n[*] 使用 scene_count={scene_count} 运行 pipeline...")

    cleanup_old_output()
    prepare_input_json()

    input_data = {
        "type": "text",
        "content": "这是一个测试文本。\n用来验证scene_count的控制能力。\n系统应该按照指定的scene数量生成。"
    }

    try:
        code = (
            "import run_pipeline_user; "
            f"input_data={repr(input_data)}; "
            f"run_pipeline_user.run_pipeline(input_data, scene_count={repr(scene_count)})"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            cwd=str(PROJECT_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=SUBPROCESS_ENV,
            timeout=1800,
        )

        final_scene_count = read_scene_plan()
        generated_audio_count = count_generated_audio_files()
        missing_audio_count = count_missing_audio_files(final_scene_count)
        video_warn_audio_missing = result.stdout.count("[VIDEO][WARN] 音频不存在") + result.stderr.count("[VIDEO][WARN] 音频不存在")

        success = (
            result.returncode == 0
            and OUTPUT_VIDEO_PATH.exists()
            and generated_audio_count == final_scene_count
            and missing_audio_count == 0
            and video_warn_audio_missing == 0
        )

        return {
            "success": success,
            "error_message": "" if result.returncode == 0 else (result.stderr or result.stdout)[-500:],
            "final_scene_count": final_scene_count,
            "target_scene_count": scene_count if scene_count is not None else -1,
            "real_content_part_count": extract_metric(result.stdout, "real_content_part_count"),
            "fallback_count": extract_metric(result.stdout, "fallback_count"),
            "generated_audio_count": generated_audio_count,
            "missing_audio_count": missing_audio_count,
            "video_exists": OUTPUT_VIDEO_PATH.exists(),
            "video_warn_audio_missing": video_warn_audio_missing,
            "stdout": result.stdout,
            "stderr": result.stderr,
        }
    except Exception as e:
        final_scene_count = read_scene_plan()
        return {
            "success": False,
            "error_message": str(e),
            "final_scene_count": final_scene_count,
            "target_scene_count": scene_count if scene_count is not None else -1,
            "real_content_part_count": -1,
            "fallback_count": -1,
            "generated_audio_count": count_generated_audio_files(),
            "missing_audio_count": count_missing_audio_files(final_scene_count),
            "video_exists": OUTPUT_VIDEO_PATH.exists(),
            "video_warn_audio_missing": 0,
            "stdout": "",
            "stderr": "",
        }


def run_pipeline_with_text(scene_count, content: str):
    cleanup_old_output()
    input_data = {"type": "text", "content": content}
    safe_write_json(INPUT_JSON_PATH, input_data)

    code = (
        "import run_pipeline_user; "
        f"input_data={repr(input_data)}; "
        f"run_pipeline_user.run_pipeline(input_data, scene_count={repr(scene_count)})"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=SUBPROCESS_ENV,
        timeout=1800,
    )

    final_scene_count = read_scene_plan()
    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "target_scene_count": scene_count if scene_count is not None else -1,
        "final_scene_count": final_scene_count,
        "real_content_part_count": extract_metric(result.stdout, "real_content_part_count"),
        "fallback_count": extract_metric(result.stdout, "fallback_count"),
        "generated_audio_count": count_generated_audio_files(),
        "missing_audio_count": count_missing_audio_files(final_scene_count),
        "video_exists": OUTPUT_VIDEO_PATH.exists(),
        "video_warn_audio_missing": result.stdout.count("[VIDEO][WARN] 音频不存在") + result.stderr.count("[VIDEO][WARN] 音频不存在"),
    }


def video_exists() -> bool:
    """检查输出视频是否存在。"""
    return OUTPUT_VIDEO_PATH.exists()


def print_case_header(case_name: str):
    """打印测试case的标题。"""
    print("\n" + "=" * 70)
    print(f"[TEST] {case_name}")
    print("=" * 70)


def print_case_result(case_name: str, passed: bool, reason: str = ""):
    """打印case结果。"""
    status = "Y" if passed else "N"
    print(f"[{status}] {case_name}")
    if reason and not passed:
        print(f"    原因：{reason}")


TEST_RESULTS = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "failures": []
}


def record_result(case_name: str, passed: bool, reason: str = ""):
    """记录测试结果。"""
    TEST_RESULTS["total"] += 1
    if passed:
        TEST_RESULTS["passed"] += 1
    else:
        TEST_RESULTS["failed"] += 1
        TEST_RESULTS["failures"].append(f"{case_name}: {reason}")
    print_case_result(case_name, passed, reason)


def case_1_default_auto_mode() -> bool:
    """
    Case 1：默认自动模式
    
    验证：不传 scene_count 时，系统保持自动逻辑，生成 3 个 scene。
    """
    print_case_header("Case 1 - 默认自动模式（scene_count=None）")
    
    result = run_pipeline_by_scene_count(None)

    if not result["success"]:
        record_result("Case 1 - 默认自动模式", False, f"pipeline 执行失败：{result['error_message']}")
        return False

    if not result["video_exists"]:
        record_result("Case 1 - 默认自动模式", False, "视频文件不存在")
        return False

    if result["final_scene_count"] == 0:
        record_result("Case 1 - 默认自动模式", False, "无法读取 scene_plan.json")
        return False

    if result["final_scene_count"] != 3:
        record_result("Case 1 - 默认自动模式", False, f"期望 3 个 scene，实际 {result['final_scene_count']} 个")
        return False

    if result["generated_audio_count"] != 3 or result["missing_audio_count"] != 0:
        record_result("Case 1 - 默认自动模式", False, f"音频不完整：generated={result['generated_audio_count']} missing={result['missing_audio_count']}")
        return False

    if result["video_warn_audio_missing"] != 0:
        record_result("Case 1 - 默认自动模式", False, f"检测到音频缺失 warning：{result['video_warn_audio_missing']} 次")
        return False

    print(f"[PASS] target_scene_count=auto | final_scene_count={result['final_scene_count']} | real_content_part_count={result['real_content_part_count']} | fallback_count={result['fallback_count']} | generated_audio_count={result['generated_audio_count']}")
    record_result("Case 1 - 默认自动模式", True)
    return True


def case_2_fixed_3_scenes() -> bool:
    """
    Case 2：显式指定 3 个 scene
    
    验证：scene_count=3 时，最终生成 3 个 scene。
    """
    print_case_header("Case 2 - 显式指定 3 个 scene")
    
    result = run_pipeline_by_scene_count(3)

    if not result["success"]:
        record_result("Case 2 - 显式指定 3", False, f"pipeline 执行失败：{result['error_message']}")
        return False

    if not result["video_exists"]:
        record_result("Case 2 - 显式指定 3", False, "视频文件不存在")
        return False

    if result["final_scene_count"] == 0:
        record_result("Case 2 - 显式指定 3", False, "无法读取 scene_plan.json")
        return False

    if result["final_scene_count"] != 3:
        record_result("Case 2 - 显式指定 3", False, f"期望 3 个 scene，实际 {result['final_scene_count']} 个")
        return False

    if result["generated_audio_count"] != 3 or result["missing_audio_count"] != 0:
        record_result("Case 2 - 显式指定 3", False, f"音频不完整：generated={result['generated_audio_count']} missing={result['missing_audio_count']}")
        return False

    if result["video_warn_audio_missing"] != 0:
        record_result("Case 2 - 显式指定 3", False, f"检测到音频缺失 warning：{result['video_warn_audio_missing']} 次")
        return False

    print(f"[PASS] target_scene_count=3 | final_scene_count={result['final_scene_count']} | real_content_part_count={result['real_content_part_count']} | fallback_count={result['fallback_count']} | generated_audio_count={result['generated_audio_count']}")
    record_result("Case 2 - 显式指定 3", True)
    return True



def case_3_fixed_5_scenes() -> bool:
    """
    Case 3：显式指定 5 个 scene
    
    验证：scene_count=5 时，最终生成 5 个 scene。
    """
    print_case_header("Case 3 - 显式指定 5 个 scene")
    
    result = run_pipeline_with_text(
        5,
        "第一句说明背景。第二句补充重点。第三句解释原因。第四句说明结果。第五句给出结论。"
    )

    if result["returncode"] != 0:
        record_result("Case 3 - 显式指定 5", False, f"pipeline 执行失败：{result['stderr'][-300:] or result['stdout'][-300:]}")
        return False

    if not result["video_exists"]:
        record_result("Case 3 - 显式指定 5", False, "视频文件不存在")
        return False

    if result["final_scene_count"] == 0:
        record_result("Case 3 - 显式指定 5", False, "无法读取 scene_plan.json")
        return False

    if result["final_scene_count"] != 5:
        record_result("Case 3 - 显式指定 5", False, f"期望 5 个 scene，实际 {result['final_scene_count']} 个")
        return False

    if result["generated_audio_count"] != 5 or result["missing_audio_count"] != 0:
        record_result("Case 3 - 显式指定 5", False, f"音频不完整：generated={result['generated_audio_count']} missing={result['missing_audio_count']}")
        return False

    if result["video_warn_audio_missing"] != 0:
        record_result("Case 3 - 显式指定 5", False, f"检测到音频缺失 warning：{result['video_warn_audio_missing']} 次")
        return False

    if result["fallback_count"] not in (0, -1) and result["fallback_count"] != 0:
        record_result("Case 3 - 显式指定 5", False, f"中等文本 fixed 5 不应触发 fallback，实际 {result['fallback_count']} 次")
        return False

    print(f"[PASS] target_scene_count=5 | final_scene_count={result['final_scene_count']} | real_content_part_count={result['real_content_part_count']} | fallback_count={result['fallback_count']} | generated_audio_count={result['generated_audio_count']}")
    record_result("Case 3 - 显式指定 5", True)
    return True


def case_4_no_state_pollution() -> bool:
    """
    Case 4：连续运行无污染

    验证：第一次运行 scene_count=5，第二次不传 scene_count，
    第二次必须回到自动模式。
    """
    print_case_header("Case 4 - 连续运行无污染")

    result_1 = run_pipeline_by_scene_count(5)
    if not result_1["success"]:
        record_result("Case 4 - 连续运行无污染", False, f"首次运行失败：{result_1['error_message']}")
        return False

    result_2 = run_pipeline_by_scene_count(None)
    if not result_2["success"]:
        record_result("Case 4 - 连续运行无污染", False, f"第二次运行失败：{result_2['error_message']}")
        return False

    if result_1["final_scene_count"] != 5:
        record_result("Case 4 - 连续运行无污染", False, f"首次运行期望 5 个 scene，实际 {result_1['final_scene_count']} 个")
        return False

    if result_2["final_scene_count"] != 3:
        record_result("Case 4 - 连续运行无污染", False, f"第二次运行应回到自动模式 3 个 scene，实际 {result_2['final_scene_count']} 个")
        return False

    if result_1["missing_audio_count"] != 0 or result_2["missing_audio_count"] != 0:
        record_result("Case 4 - 连续运行无污染", False, "连续运行后存在音频缺失")
        return False

    print(f"[PASS] 连续运行无污染：第一次 {result_1['final_scene_count']} 个，第二次 {result_2['final_scene_count']} 个")
    record_result("Case 4 - 连续运行无污染", True)
    return True


def case_5_short_text_fixed_5() -> bool:
    """
    Case 5：短文本边界验证

    验证：较短文本在 scene_count=5 时也不会出现音频缺失。
    """
    print_case_header("Case 5 - 短文本 + 固定 5 个 scene")

    result = run_pipeline_with_text(5, "这是短文本，但是包含两句。请继续阅读下一句。")

    if result["returncode"] != 0:
        record_result("Case 5 - 短文本 + 固定 5", False, f"pipeline 执行失败：{result['stderr'][-300:] or result['stdout'][-300:]}")
        return False

    if result["final_scene_count"] != 5:
        record_result("Case 5 - 短文本 + 固定 5", False, f"期望 5 个 scene，实际 {result['final_scene_count']} 个")
        return False

    if result["generated_audio_count"] != 5 or result["missing_audio_count"] != 0:
        record_result("Case 5 - 短文本 + 固定 5", False, f"音频不完整：generated={result['generated_audio_count']} missing={result['missing_audio_count']}")
        return False

    if result["video_warn_audio_missing"] != 0:
        record_result("Case 5 - 短文本 + 固定 5", False, f"检测到音频缺失 warning：{result['video_warn_audio_missing']} 次")
        return False

    if not result["video_exists"]:
        record_result("Case 5 - 短文本 + 固定 5", False, "视频文件不存在")
        return False

    if result["fallback_count"] < 0:
        record_result("Case 5 - 短文本 + 固定 5", False, "未读取到 fallback_count 日志")
        return False

    print(f"[PASS] target_scene_count=5 | final_scene_count={result['final_scene_count']} | real_content_part_count={result['real_content_part_count']} | fallback_count={result['fallback_count']} | generated_audio_count={result['generated_audio_count']}")
    record_result("Case 5 - 短文本 + 固定 5", True)
    return True


def case_6_extreme_short_text_fixed_5() -> bool:
    """
    Case 6：极短文本边界验证

    验证：即使文本极短，也先尝试真实内容复用，再考虑 fallback。
    """
    print_case_header("Case 6 - 极短文本 + 固定 5 个 scene")

    result = run_pipeline_with_text(5, "测试。")

    if result["returncode"] != 0:
        record_result("Case 6 - 极短文本 + 固定 5", False, f"pipeline 执行失败：{result['stderr'][-300:] or result['stdout'][-300:]}")
        return False

    if result["final_scene_count"] != 5:
        record_result("Case 6 - 极短文本 + 固定 5", False, f"期望 5 个 scene，实际 {result['final_scene_count']} 个")
        return False

    if result["generated_audio_count"] != 5 or result["missing_audio_count"] != 0:
        record_result("Case 6 - 极短文本 + 固定 5", False, f"音频不完整：generated={result['generated_audio_count']} missing={result['missing_audio_count']}")
        return False

    if result["video_warn_audio_missing"] != 0:
        record_result("Case 6 - 极短文本 + 固定 5", False, f"检测到音频缺失 warning：{result['video_warn_audio_missing']} 次")
        return False

    if result["fallback_count"] < 0:
        record_result("Case 6 - 极短文本 + 固定 5", False, "未读取到 fallback_count 日志")
        return False

    print(f"[PASS] target_scene_count=5 | final_scene_count={result['final_scene_count']} | real_content_part_count={result['real_content_part_count']} | fallback_count={result['fallback_count']} | generated_audio_count={result['generated_audio_count']}")
    record_result("Case 6 - 极短文本 + 固定 5", True)
    return True


def print_summary():
    """打印最终汇总。"""
    print("\n" + "=" * 80)
    print("[SUMMARY] Scene Count 控制能力测试汇总")
    print("=" * 80)

    print("\ncase_name | target_scene_count | final_scene_count | real_content_part_count | fallback_count | generated_audio_count | success")
    print("-" * 80)
    print(f"总计：{TEST_RESULTS['total']} 个 case")
    print(f"通过：{TEST_RESULTS['passed']} 个")
    print(f"失败：{TEST_RESULTS['failed']} 个")
    
    if TEST_RESULTS['failures']:
        print("\n[FAILURES] 失败详情：")
        for failure in TEST_RESULTS['failures']:
            print(f"  - {failure}")
    
    print("=" * 80)


if __name__ == "__main__":
    print("=" * 80)
    print("[TEST SUITE] Scene Count 控制能力测试")
    print("=" * 80)
    print(f"项目根目录：{PROJECT_ROOT}")
    print(f"Scene Plan：{SCENE_PLAN_CURRENT}")
    print(f"输出视频：{OUTPUT_VIDEO_PATH}")
    print()
    
    try:
        # 运行 6 个 test case
        case_1_default_auto_mode()
        case_2_fixed_3_scenes()
        case_3_fixed_5_scenes()
        case_4_no_state_pollution()
        case_5_short_text_fixed_5()
        case_6_extreme_short_text_fixed_5()
        
        # 打印汇总
        print_summary()
        
        # 返回适当的exit code
        sys.exit(0 if TEST_RESULTS['failed'] == 0 else 1)
    
    except Exception as e:
        print(f"\n[ERROR] 测试异常：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
