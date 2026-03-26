# -*- coding: utf-8 -*-
"""
validate_stability.py

独立稳定性验证工具：
1. 多轮执行主链验证
2. 统计成功率、视频产出率
3. 统计 bridge / fallback / 异常次数
4. 输出控制台摘要与 JSON 报告
"""

from __future__ import annotations

import argparse
import os
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT_FOR_IMPORT = CURRENT_FILE.parent.parent
if str(PROJECT_ROOT_FOR_IMPORT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT_FOR_IMPORT))

from modules import project_paths


PROJECT_ROOT = getattr(
    project_paths,
    "PROJECT_ROOT",
    project_paths.get_project_root(),
)
DATA_CURRENT_DIR = getattr(
    project_paths,
    "DATA_CURRENT_DIR",
    project_paths.get_data_current_dir(),
)
OUTPUT_DIR = getattr(
    project_paths,
    "OUTPUT_DIR",
    project_paths.get_project_root() / "output",
)
SCRIPT_FILE = getattr(
    project_paths,
    "SCRIPT_JSON_PATH",
    project_paths.get_project_root() / "script.json",
)
SCENE_PLAN_FILE = getattr(
    project_paths,
    "CURRENT_SCENE_PLAN_JSON_PATH",
    project_paths.get_data_current_dir() / "scene_plan.json",
)
SCENE_ASSETS_FILE = getattr(
    project_paths,
    "SCENE_ASSETS_JSON_PATH",
    project_paths.get_data_current_dir() / "scene_assets.json",
)
OUTPUT_VIDEO_FILE = getattr(
    project_paths,
    "OUTPUT_VIDEO_FILE",
    OUTPUT_DIR / "video.mp4",
)
REPORT_FILE = getattr(
    project_paths,
    "STABILITY_REPORT_FILE",
    OUTPUT_DIR / "stability_report.json",
)
RUN_PIPELINE_SCRIPT = getattr(
    project_paths,
    "RUN_PIPELINE_SCRIPT",
    project_paths.get_project_root() / "run_pipeline_web.py",
)
BUILD_SCENE_ASSETS_SCRIPT = getattr(
    project_paths,
    "BUILD_SCENE_ASSETS_SCRIPT",
    project_paths.get_project_root() / "build_scene_assets.py",
)
SCENE_PLANNER_SCRIPT = getattr(
    project_paths,
    "SCENE_PLANNER_SCRIPT",
    project_paths.get_project_root() / "scene_planner.py",
)

PIPELINE_MARKER = "[PIPELINE]"
BUILD_ASSETS_MARKER = "[BUILD_ASSETS]"
ASSET_MAIN_MARKER = "[ASSET][MAIN]"
ASSET_MAIN_ERROR_MARKER = "[ASSET][MAIN][ERROR]"
FALLBACK_MARKER = "fallback"
ERROR_MARKERS = ["ERROR", "Traceback", "Exception"]


@dataclass
class ArtifactStatus:
    exists: bool
    size: int
    mtime_ns: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="VIDEO_AGENT stability validator")
    parser.add_argument("--runs", type=int, default=3, help="验证轮数，默认 3")
    return parser.parse_args()


def ensure_report_directory() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def read_file_status(path: Path) -> ArtifactStatus:
    if not path.exists():
        return ArtifactStatus(exists=False, size=0, mtime_ns=0)
    try:
        stat_result = path.stat()
        return ArtifactStatus(
            exists=True,
            size=stat_result.st_size,
            mtime_ns=stat_result.st_mtime_ns,
        )
    except OSError:
        return ArtifactStatus(exists=True, size=0, mtime_ns=0)


def parse_log_metrics(output_text: str) -> Dict[str, int]:
    if not isinstance(output_text, str):
        print("[VALIDATION][WARN] 日志解析输入不是字符串，按空日志处理")
        output_text = ""

    lowered = output_text.lower()
    error_count = sum(output_text.count(marker) for marker in ERROR_MARKERS)

    return {
        "pipeline_count": output_text.count(PIPELINE_MARKER),
        "build_assets_count": output_text.count(BUILD_ASSETS_MARKER),
        "asset_main_count": output_text.count(ASSET_MAIN_MARKER),
        "asset_main_error_count": output_text.count(ASSET_MAIN_ERROR_MARKER),
        "fallback_count": lowered.count(FALLBACK_MARKER),
        "error_count": error_count,
    }


def check_output_files() -> Dict[str, Any]:
    video_status = read_file_status(OUTPUT_VIDEO_FILE)
    scene_assets_status = read_file_status(SCENE_ASSETS_FILE)
    scene_plan_status = read_file_status(SCENE_PLAN_FILE)
    script_status = read_file_status(SCRIPT_FILE)

    return {
        "video_exists": video_status.exists,
        "video_size": video_status.size,
        "video_mtime_ns": video_status.mtime_ns,
        "scene_assets_exists": scene_assets_status.exists,
        "scene_assets_size": scene_assets_status.size,
        "scene_assets_mtime_ns": scene_assets_status.mtime_ns,
        "scene_plan_exists": scene_plan_status.exists,
        "scene_plan_size": scene_plan_status.size,
        "scene_plan_mtime_ns": scene_plan_status.mtime_ns,
        "script_exists": script_status.exists,
        "script_size": script_status.size,
        "script_mtime_ns": script_status.mtime_ns,
    }


def run_python_script(script_path: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return subprocess.run(
        [sys.executable, str(script_path)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def artifact_updated(before: Dict[str, Any], after: Dict[str, Any], prefix: str) -> bool:
    exists_key = f"{prefix}_exists"
    size_key = f"{prefix}_size"
    mtime_key = f"{prefix}_mtime_ns"

    if not after.get(exists_key, False):
        return False

    if not before.get(exists_key, False):
        return True

    return (
        before.get(mtime_key, 0) != after.get(mtime_key, 0)
        or before.get(size_key, 0) != after.get(size_key, 0)
    )


def run_once(run_index: int) -> Dict[str, Any]:
    print(f"[VALIDATION] 第 {run_index} 轮：开始执行主链验证")

    before_files = check_output_files()
    process = run_python_script(RUN_PIPELINE_SCRIPT)
    output_text = f"{process.stdout or ''}\n{process.stderr or ''}".strip()
    metrics = parse_log_metrics(output_text)
    files = check_output_files()
    video_updated = artifact_updated(before_files, files, "video")
    scene_assets_updated = artifact_updated(before_files, files, "scene_assets")
    scene_plan_updated = artifact_updated(before_files, files, "scene_plan")
    script_updated = artifact_updated(before_files, files, "script")

    success = (
        process.returncode == 0
        and files["video_exists"]
        and files["video_size"] > 0
        and video_updated
    )

    if success:
        print(f"[VALIDATION] 第 {run_index} 轮：成功")
    else:
        reason_parts = []
        if process.returncode != 0:
            reason_parts.append(f"returncode={process.returncode}")
        if not files["video_exists"]:
            reason_parts.append("video.mp4 不存在")
        elif files["video_size"] <= 0:
            reason_parts.append("video.mp4 大小为 0")
        if not reason_parts:
            reason_parts.append("未知原因")
        print(f"[VALIDATION] 第 {run_index} 轮：失败（原因：{' | '.join(reason_parts)}）")

    return {
        "run_index": run_index,
        "success": success,
        "return_code": process.returncode,
        **files,
        **metrics,
        "video_updated": video_updated,
        "scene_assets_updated": scene_assets_updated,
        "scene_plan_updated": scene_plan_updated,
        "script_updated": script_updated,
        "stdout_preview": (process.stdout or "")[-4000:],
        "stderr_preview": (process.stderr or "")[-2000:],
    }


def summarize_results(all_runs: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_runs = len(all_runs)
    success_runs = sum(1 for item in all_runs if item["success"])
    failed_runs = total_runs - success_runs
    video_success_runs = sum(1 for item in all_runs if item["video_updated"] and item["video_size"] > 0)

    summary = {
        "total_runs": total_runs,
        "success_runs": success_runs,
        "failed_runs": failed_runs,
        "success_rate": round(success_runs / total_runs, 4) if total_runs else 0.0,
        "video_success_rate": round(video_success_runs / total_runs, 4) if total_runs else 0.0,
        "asset_main_count": sum(item["asset_main_count"] for item in all_runs),
        "asset_main_error_count": sum(item["asset_main_error_count"] for item in all_runs),
        "fallback_count": sum(item["fallback_count"] for item in all_runs),
        "error_count": sum(item["error_count"] for item in all_runs),
        "runs": all_runs,
    }
    return summary


def write_report(summary: Dict[str, Any]) -> Path:
    ensure_report_directory()
    with open(REPORT_FILE, "w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)
    return REPORT_FILE


def print_summary(summary: Dict[str, Any]) -> None:
    print("\n[SUMMARY]")
    print(f"总轮数：{summary['total_runs']}")
    print(f"成功轮数：{summary['success_runs']}")
    print(f"失败轮数：{summary['failed_runs']}")
    print(f"成功率：{summary['success_rate'] * 100:.2f}%")
    print(f"video 生成成功率：{summary['video_success_rate'] * 100:.2f}%")
    print(f"ASSET MAIN 命中次数：{summary['asset_main_count']}")
    print(f"ASSET MAIN ERROR 次数：{summary['asset_main_error_count']}")
    print(f"fallback 次数：{summary['fallback_count']}")
    print(f"异常次数：{summary['error_count']}")
    print(f"报告文件：{REPORT_FILE}")


def main() -> int:
    args = parse_args()
    requested_runs = max(1, int(args.runs))

    print(f"[VALIDATION] 项目根路径：{PROJECT_ROOT}")
    print(f"[VALIDATION] 当前数据目录：{DATA_CURRENT_DIR}")
    print(f"[VALIDATION] 当前输出目录：{OUTPUT_DIR}")
    print(f"[VALIDATION] 当前主链脚本：{RUN_PIPELINE_SCRIPT}")
    print(f"[VALIDATION] 当前报告路径：{REPORT_FILE}")

    all_runs: List[Dict[str, Any]] = []
    for run_index in range(1, requested_runs + 1):
        try:
            all_runs.append(run_once(run_index))
        except Exception as error:
            print(f"[VALIDATION][WARN] 第 {run_index} 轮日志采集异常：{error}")
            all_runs.append(
                {
                    "run_index": run_index,
                    "success": False,
                    "return_code": -1,
                    "video_exists": False,
                    "video_size": 0,
                    "video_mtime_ns": 0,
                    "scene_assets_exists": False,
                    "scene_assets_size": 0,
                    "scene_assets_mtime_ns": 0,
                    "scene_plan_exists": False,
                    "scene_plan_size": 0,
                    "scene_plan_mtime_ns": 0,
                    "script_exists": False,
                    "script_size": 0,
                    "script_mtime_ns": 0,
                    "pipeline_count": 0,
                    "build_assets_count": 0,
                    "asset_main_count": 0,
                    "asset_main_error_count": 0,
                    "fallback_count": 0,
                    "error_count": 1,
                    "video_updated": False,
                    "scene_assets_updated": False,
                    "scene_plan_updated": False,
                    "script_updated": False,
                    "stdout_preview": "",
                    "stderr_preview": str(error),
                }
            )

    summary = summarize_results(all_runs)
    report_path = write_report(summary)
    print_summary(summary)

    report_status = read_file_status(report_path)
    if not report_status.exists or report_status.size <= 0:
        print(f"[VALIDATION][WARN] 报告文件写出异常：{report_path}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())