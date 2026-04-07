# -*- coding: utf-8 -*-
"""
Isolated scheduler integration verification runner.

职责：
1. 读取 scheduler_ready_plan.json
2. 转换为 scheduler_input_plan
3. 解析并调用真实 scene_clip_scheduler 入口
4. 打印结构结果

注意：
- 不接入主链
- 不触发 render
- 不进入 video_engine
"""

from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.content_processor.scheduler_integration_adapter import build_scheduler_input_plan


SCHEDULER_READY_PLAN_PATH = PROJECT_ROOT / "data" / "current" / "scheduler_ready_plan.json"


def _load_scheduler_ready_plan() -> dict:
    if not SCHEDULER_READY_PLAN_PATH.exists():
        raise FileNotFoundError(f"scheduler_ready_plan.json not found: {SCHEDULER_READY_PLAN_PATH}")

    with SCHEDULER_READY_PLAN_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("scheduler_ready_plan.json must contain a JSON object")
    return data


def _resolve_scene_clip_scheduler():
    candidate_imports = [
        ("modules.scene_clip_scheduler", "scene_clip_scheduler"),
        ("scene_clip_scheduler", "scene_clip_scheduler"),
        ("modules.scene_clip_scheduler", "run"),
        ("scene_clip_scheduler", "run"),
    ]

    for module_name, attr_name in candidate_imports:
        try:
            module = __import__(module_name, fromlist=[attr_name])
        except Exception:
            continue

        scheduler_callable = getattr(module, attr_name, None)
        if callable(scheduler_callable):
            return scheduler_callable

    raise RuntimeError("scene_clip_scheduler callable not found in workspace")


def run_m4_scheduler_test():
    print("[M4] scheduler integration test start")
    scheduler_ready_plan = _load_scheduler_ready_plan()
    scheduler_input_plan = build_scheduler_input_plan(scheduler_ready_plan)
    scenes = scheduler_input_plan.get("scenes", []) if isinstance(scheduler_input_plan, dict) else []
    print(f"[M4] scene_count={len(scenes)}")

    scene_clip_scheduler = _resolve_scene_clip_scheduler()
    print("[M4] calling scene_clip_scheduler")
    result = scene_clip_scheduler(scheduler_input_plan)
    print("[M4] scheduler returned")
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    print("[M4] done")
    return result


if __name__ == "__main__":
    run_m4_scheduler_test()