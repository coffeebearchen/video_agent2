from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS_ROOT = PROJECT_ROOT / "output" / "highlight_ab" / "artifacts"
CONFIG_PATH = PROJECT_ROOT / "config" / "highlight_keywords.json"
SCENE_PLAN_PATH = PROJECT_ROOT / "data" / "current" / "scene_plan.json"
OUTPUT_VIDEO_PATH = PROJECT_ROOT / "output" / "video.mp4"
CASE_RUNNER_PATH = PROJECT_ROOT / "runner" / "task_v2_pipeline_case_runner.py"
REPORT_PATH = PROJECT_ROOT / "output" / "highlight_ab" / "ab_results_minimal.json"
TOPIC = {
    "slug": "topic1_interest_rates",
    "title": "利率为什么决定资产价格",
    "input_data": {
        "type": "text",
        "content": (
            "利率为什么决定资产价格？因为利率改变资金的折现方式，也会改变未来现金流在今天值多少钱。"
            "当利率上升时，远期收益的吸引力会下降，资产估值通常承压。反过来，当利率下降时，"
            "增长型资产往往更容易获得更高定价。最后，市场并不只看利率本身，还会看利率预期如何变化。"
        ),
    },
}


@dataclass
class FileState:
    path: str
    exists: bool
    size: int | None
    mtime: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "exists": self.exists,
            "size": self.size,
            "mtime": self.mtime,
            "mtime_iso": isoformat_timestamp(self.mtime),
        }


def isoformat_timestamp(timestamp: float | None) -> str | None:
    if timestamp is None:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).astimezone().isoformat()


def tail_text(text: str, max_lines: int = 20) -> list[str]:
    lines = text.splitlines()
    if not lines:
        return []
    return lines[-max_lines:]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def capture_file_state(path: Path) -> FileState:
    if not path.exists():
        return FileState(path=str(path), exists=False, size=None, mtime=None)
    stat = path.stat()
    return FileState(path=str(path), exists=True, size=stat.st_size, mtime=stat.st_mtime)


def file_state_from_dict(data: dict[str, Any]) -> FileState:
    return FileState(
        path=str(data.get("path", "")),
        exists=bool(data.get("exists", False)),
        size=data.get("size"),
        mtime=data.get("mtime"),
    )


def remove_if_exists(path: Path) -> dict[str, Any]:
    before = capture_file_state(path)
    removed = False
    if path.exists():
        last_error: PermissionError | None = None
        for _ in range(20):
            try:
                path.unlink()
                removed = True
                last_error = None
                break
            except PermissionError as error:
                last_error = error
                time.sleep(0.5)
        if last_error is not None:
            raise last_error
    after = capture_file_state(path)
    return {
        "before": before.to_dict(),
        "removed": removed,
        "after": after.to_dict(),
    }


def load_scene_summary(scene_plan_file: Path) -> tuple[int, list[dict[str, Any]]]:
    if not scene_plan_file.exists():
        return 0, []
    scene_plan = read_json(scene_plan_file)
    scenes = scene_plan.get("scenes", []) if isinstance(scene_plan, dict) else []
    highlights = []
    for scene in scenes:
        highlights.append(
            {
                "scene_id": scene.get("scene_id"),
                "text": scene.get("text", ""),
                "highlights": scene.get("highlights", []),
            }
        )
    return len(scenes), highlights


def build_newness_report(
    before: FileState,
    after: FileState,
    run_started_at: float,
    cleanup_removed: bool,
) -> dict[str, Any]:
    is_new = False
    reasons: list[str] = []

    if cleanup_removed and after.exists:
        is_new = True
        reasons.append("old_file_removed_before_run_and_new_file_exists_after_run")
    if after.exists and after.mtime is not None and after.mtime >= run_started_at:
        is_new = True
        reasons.append("mtime_is_after_run_start")
    if before.exists and after.exists:
        if before.size != after.size:
            is_new = True
            reasons.append("size_changed_from_pre_run_state")
        if before.mtime != after.mtime:
            is_new = True
            reasons.append("mtime_changed_from_pre_run_state")
    if not before.exists and after.exists:
        is_new = True
        reasons.append("file_absent_before_run_and_present_after_run")

    if not reasons:
        reasons.append("no_new_file_signal_detected")

    return {
        "is_new": is_new,
        "before": before.to_dict(),
        "after": after.to_dict(),
        "cleanup_removed": cleanup_removed,
        "basis": reasons,
    }


def run_case(topic: dict[str, Any], variant: str, config_payload: dict[str, Any]) -> dict[str, Any]:
    case_slug = f"{topic['slug']}_{variant}"
    case_dir = ARTIFACTS_ROOT / case_slug
    if case_dir.exists():
        shutil.rmtree(case_dir)
    case_dir.mkdir(parents=True, exist_ok=True)

    input_file = case_dir / "input.json"
    write_json(input_file, topic["input_data"])
    write_json(case_dir / "highlight_config_used.json", config_payload)

    cleanup_scene_plan = remove_if_exists(SCENE_PLAN_PATH)
    cleanup_video = remove_if_exists(OUTPUT_VIDEO_PATH)

    before_scene_plan = file_state_from_dict(cleanup_scene_plan["before"])
    before_video = file_state_from_dict(cleanup_video["before"])

    CONFIG_PATH.write_text(
        json.dumps(config_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    env["VIDEO_AGENT_NON_INTERACTIVE"] = "1"
    env["CI"] = "1"
    run_started_at = datetime.now().timestamp()
    command = [
        sys.executable,
        str(CASE_RUNNER_PATH),
        "--input-file",
        str(input_file),
        "--scene-count",
        "5",
    ]
    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        stdin=subprocess.DEVNULL,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )

    stdout_text = result.stdout
    stderr_text = result.stderr
    (case_dir / "stdout.log").write_text(stdout_text, encoding="utf-8")
    (case_dir / "stderr.log").write_text(stderr_text, encoding="utf-8")

    after_scene_plan = capture_file_state(SCENE_PLAN_PATH)
    after_video = capture_file_state(OUTPUT_VIDEO_PATH)

    if SCENE_PLAN_PATH.exists():
        shutil.copy2(SCENE_PLAN_PATH, case_dir / "scene_plan.json")
    if OUTPUT_VIDEO_PATH.exists():
        shutil.copy2(OUTPUT_VIDEO_PATH, case_dir / "video.mp4")

    scene_plan_copy = case_dir / "scene_plan.json"
    final_scene_count, scene_highlights = load_scene_summary(scene_plan_copy)

    summary = {
        "topic": topic["title"],
        "variant": variant,
        "highlight_enabled": bool(config_payload.get("enable_highlight", True)),
        "returncode": result.returncode,
        "command": command,
        "input_file": str(input_file),
        "scene_plan_exists": scene_plan_copy.exists(),
        "video_exists": (case_dir / "video.mp4").exists(),
        "final_scene_count": final_scene_count,
        "scene_highlights": scene_highlights,
        "stdout_tail": tail_text(stdout_text),
        "stderr_tail": tail_text(stderr_text),
        "cleanup": {
            "scene_plan": cleanup_scene_plan,
            "video": cleanup_video,
        },
        "scene_plan_newness": build_newness_report(
            before_scene_plan,
            after_scene_plan,
            run_started_at,
            cleanup_scene_plan["removed"],
        ),
        "video_newness": build_newness_report(
            before_video,
            after_video,
            run_started_at,
            cleanup_video["removed"],
        ),
    }
    write_json(case_dir / "summary.json", summary)
    return summary


def main() -> int:
    ARTIFACTS_ROOT.mkdir(parents=True, exist_ok=True)
    original_config_text = CONFIG_PATH.read_text(encoding="utf-8")
    normal_config = json.loads(original_config_text)
    disabled_config = {
        "enable_highlight": False,
        "industrial_keywords": [
            "几乎不会命中的词A",
            "几乎不会命中的词B",
        ]
    }

    results: list[dict[str, Any]] = []
    try:
        results.append(run_case(TOPIC, "A", normal_config))
        results.append(run_case(TOPIC, "B", disabled_config))
    finally:
        CONFIG_PATH.write_text(original_config_text, encoding="utf-8")

    write_json(REPORT_PATH, results)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())