# -*- coding: utf-8 -*-
"""
tests/test_highlight_layer_runner.py

Task34 - Highlight Layer 独立验收脚本
"""

import io
import json
import os
import sys
import subprocess
from pathlib import Path

if (sys.stdout.encoding or "").lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules import project_paths

SCENE_PLAN_PATH = project_paths.get_data_current_dir() / "scene_plan.json"
SCENE_ASSETS_PATH = project_paths.get_data_current_dir() / "scene_assets.json"
OUTPUT_VIDEO_PATH = project_paths.get_project_root() / "output" / "video.mp4"
AUDIO_DIR = project_paths.get_project_root() / "audio"
INPUT_JSON_PATH = project_paths.get_project_root() / "input.json"

SUBPROCESS_ENV = os.environ.copy()
SUBPROCESS_ENV["PYTHONIOENCODING"] = "utf-8"
SUBPROCESS_ENV["PYTHONUTF8"] = "1"

TEST_RESULTS = {
    "total": 0,
    "passed": 0,
    "failed": 0,
    "failures": [],
}


def safe_read_json(path: Path):
    if not path.exists():
        return None
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def cleanup_outputs():
    if OUTPUT_VIDEO_PATH.exists():
        OUTPUT_VIDEO_PATH.unlink(missing_ok=True)
    if AUDIO_DIR.exists():
        for path in AUDIO_DIR.glob("card_*.mp3"):
            path.unlink(missing_ok=True)


def read_scene_plan_scenes():
    data = safe_read_json(SCENE_PLAN_PATH)
    if not isinstance(data, dict):
        return []
    scenes = data.get("scenes", [])
    return scenes if isinstance(scenes, list) else []


def read_scene_assets():
    data = safe_read_json(SCENE_ASSETS_PATH)
    if not isinstance(data, dict):
        return []
    assets = data.get("scene_assets", [])
    return assets if isinstance(assets, list) else []


def count_audio_files() -> int:
    if not AUDIO_DIR.exists():
        return 0
    return len(list(AUDIO_DIR.glob("card_*.mp3")))


def summarize_highlights(scenes):
    highlight_scene_count = 0
    total_highlight_count = 0
    highlight_words = []
    fallback_highlight_used = 0

    for scene in scenes:
        highlights = scene.get("highlights", [])
        if not isinstance(highlights, list):
            highlights = []
        cleaned = [str(item).strip() for item in highlights if str(item).strip()]
        if cleaned:
            highlight_scene_count += 1
            total_highlight_count += len(cleaned)
            highlight_words.extend(cleaned)
        else:
            fallback_highlight_used += 1

    return {
        "highlight_scene_count": highlight_scene_count,
        "total_highlight_count": total_highlight_count,
        "highlight_words": highlight_words,
        "fallback_highlight_used": fallback_highlight_used,
    }


def run_pipeline(text: str, scene_count=None):
    cleanup_outputs()
    input_data = {"type": "text", "content": text}
    INPUT_JSON_PATH.write_text(json.dumps(input_data, ensure_ascii=False, indent=2), encoding="utf-8")

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
        timeout=1800,
        env=SUBPROCESS_ENV,
    )

    scenes = read_scene_plan_scenes()
    assets = read_scene_assets()
    highlight_summary = summarize_highlights(scenes)
    asset_highlight_count = sum(
        len(asset.get("highlights", []))
        for asset in assets
        if isinstance(asset.get("highlights", []), list)
    )

    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "final_scene_count": len(scenes),
        "highlight_scene_count": highlight_summary["highlight_scene_count"],
        "total_highlight_count": highlight_summary["total_highlight_count"],
        "highlight_words": highlight_summary["highlight_words"],
        "fallback_highlight_used": highlight_summary["fallback_highlight_used"],
        "asset_highlight_count": asset_highlight_count,
        "generated_audio_count": count_audio_files(),
        "video_exists": OUTPUT_VIDEO_PATH.exists(),
    }


def print_case_header(case_name: str):
    print("\n" + "=" * 72)
    print(f"[TEST] {case_name}")
    print("=" * 72)


def record_result(case_name: str, passed: bool, reason: str = ""):
    TEST_RESULTS["total"] += 1
    if passed:
        TEST_RESULTS["passed"] += 1
        print(f"[Y] {case_name}")
        return
    TEST_RESULTS["failed"] += 1
    TEST_RESULTS["failures"].append(f"{case_name}: {reason}")
    print(f"[N] {case_name}")
    if reason:
        print(f"    原因：{reason}")


def ensure_basic_integrity(result, expected_scene_count: int):
    if result["returncode"] != 0:
        return False, (result["stderr"] or result["stdout"])[-500:]
    if result["final_scene_count"] != expected_scene_count:
        return False, f"scene 数量错误：期望 {expected_scene_count}，实际 {result['final_scene_count']}"
    if result["generated_audio_count"] != expected_scene_count:
        return False, f"音频数量错误：期望 {expected_scene_count}，实际 {result['generated_audio_count']}"
    if not result["video_exists"]:
        return False, "视频文件不存在"
    return True, ""


def case_1_industrial_text() -> bool:
    print_case_header("Case 1 - 标准工业文本")
    text = "高精度轴承自动化设备，为生产提供稳定与效率。设备支持连续生产，具备高精度加工能力。还能降低成本，提高一致性，并提供可靠的解决方案。"
    result = run_pipeline(text)
    ok, reason = ensure_basic_integrity(result, 3)
    if not ok:
        record_result("Case 1 - 标准工业文本", False, reason)
        return False
    if result["total_highlight_count"] <= 0:
        record_result("Case 1 - 标准工业文本", False, "未提取到任何关键词")
        return False
    if result["asset_highlight_count"] <= 0:
        record_result("Case 1 - 标准工业文本", False, "scene_assets 未透传高亮数据")
        return False
    print(f"[PASS] final_scene_count={result['final_scene_count']} | highlight_scene_count={result['highlight_scene_count']} | total_highlight_count={result['total_highlight_count']} | highlight_words={result['highlight_words'][:4]}")
    record_result("Case 1 - 标准工业文本", True)
    return True


def case_2_plain_text_safe_degrade() -> bool:
    print_case_header("Case 2 - 普通文本安全降级")
    text = "今天我们简单整理一下这个问题，然后按顺序说明发生了什么，以及接下来可以怎么理解。"
    result = run_pipeline(text)
    ok, reason = ensure_basic_integrity(result, 3)
    if not ok:
        record_result("Case 2 - 普通文本安全降级", False, reason)
        return False
    print(f"[PASS] final_scene_count={result['final_scene_count']} | highlight_scene_count={result['highlight_scene_count']} | total_highlight_count={result['total_highlight_count']} | fallback_highlight_used={result['fallback_highlight_used']}")
    record_result("Case 2 - 普通文本安全降级", True)
    return True


def case_3_scene_count_5_highlight() -> bool:
    print_case_header("Case 3 - scene_count=5 + highlight")
    text = "高精度轴承自动化设备，为生产提供稳定与效率。设备支持连续生产，并保持高一致性。系统还能降低成本，提升高效率，在多个行业中应用广泛。最终为企业提供可靠的解决方案。"
    result = run_pipeline(text, scene_count=5)
    ok, reason = ensure_basic_integrity(result, 5)
    if not ok:
        record_result("Case 3 - scene_count=5 + highlight", False, reason)
        return False
    if result["total_highlight_count"] <= 0:
        record_result("Case 3 - scene_count=5 + highlight", False, "fixed 5 模式未提取到关键词")
        return False
    print(f"[PASS] final_scene_count={result['final_scene_count']} | highlight_scene_count={result['highlight_scene_count']} | total_highlight_count={result['total_highlight_count']}")
    record_result("Case 3 - scene_count=5 + highlight", True)
    return True


def case_4_no_pollution() -> bool:
    print_case_header("Case 4 - 连续运行无污染")
    text_1 = "高精度轴承自动化设备，为生产提供稳定与效率，并保持连续生产。"
    text_2 = "今天我们只做一个简短说明，帮助理解这个主题。"
    result_1 = run_pipeline(text_1, scene_count=5)
    result_2 = run_pipeline(text_2)
    ok_1, reason_1 = ensure_basic_integrity(result_1, 5)
    if not ok_1:
        record_result("Case 4 - 连续运行无污染", False, f"首次运行失败：{reason_1}")
        return False
    ok_2, reason_2 = ensure_basic_integrity(result_2, 3)
    if not ok_2:
        record_result("Case 4 - 连续运行无污染", False, f"第二次运行失败：{reason_2}")
        return False
    if any(word in result_2["highlight_words"] for word in ["高精度", "自动化", "连续生产"]):
        record_result("Case 4 - 连续运行无污染", False, "第二次运行仍残留第一次的关键词")
        return False
    print(f"[PASS] first_highlight_count={result_1['total_highlight_count']} | second_highlight_count={result_2['total_highlight_count']}")
    record_result("Case 4 - 连续运行无污染", True)
    return True


def print_summary():
    print("\n" + "=" * 88)
    print("[SUMMARY] Highlight Layer 验收汇总")
    print("=" * 88)
    print("case_name | final_scene_count | highlight_scene_count | total_highlight_count | video_exists | success")
    print("-" * 88)
    print(f"总计：{TEST_RESULTS['total']} 个 case")
    print(f"通过：{TEST_RESULTS['passed']} 个")
    print(f"失败：{TEST_RESULTS['failed']} 个")
    if TEST_RESULTS["failures"]:
        print("\n[FAILURES] 失败详情：")
        for failure in TEST_RESULTS["failures"]:
            print(f"  - {failure}")
    print("=" * 88)


if __name__ == "__main__":
    print("=" * 88)
    print("[TEST SUITE] Highlight Layer 验收")
    print("=" * 88)
    print(f"项目根目录：{PROJECT_ROOT}")
    print(f"Scene Plan：{SCENE_PLAN_PATH}")
    print(f"Scene Assets：{SCENE_ASSETS_PATH}")
    print(f"输出视频：{OUTPUT_VIDEO_PATH}")

    case_1_industrial_text()
    case_2_plain_text_safe_degrade()
    case_3_scene_count_5_highlight()
    case_4_no_pollution()
    print_summary()
    sys.exit(0 if TEST_RESULTS["failed"] == 0 else 1)