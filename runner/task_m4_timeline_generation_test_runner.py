# -*- coding: utf-8 -*-
"""
Isolated timeline generation verification runner.

职责：
1. 读取 scheduler_ready_plan.json
2. 转换为 scheduler_input_plan
3. 调用 scene_clip_scheduler
4. 构建 timeline_plan
5. 打印结果
"""

from __future__ import annotations

import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules.content_processor.scheduler_integration_adapter import build_scheduler_input_plan
from modules.content_processor.timeline_builder import build_timeline_plan
from modules.scene_clip_scheduler import scene_clip_scheduler


SCHEDULER_READY_PLAN_PATH = PROJECT_ROOT / "data" / "current" / "scheduler_ready_plan.json"


def _load_scheduler_ready_plan() -> dict:
    if not SCHEDULER_READY_PLAN_PATH.exists():
        raise FileNotFoundError(f"scheduler_ready_plan.json not found: {SCHEDULER_READY_PLAN_PATH}")

    with SCHEDULER_READY_PLAN_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError("scheduler_ready_plan.json must contain a JSON object")
    return data


def run_m4_timeline_generation_test():
    scheduler_ready_plan = _load_scheduler_ready_plan()
    scheduler_input_plan = build_scheduler_input_plan(scheduler_ready_plan)
    scheduler_output = scene_clip_scheduler(scheduler_input_plan)
    timeline_plan = build_timeline_plan(scheduler_output)
    print(json.dumps(timeline_plan, ensure_ascii=False, indent=2, default=str))
    return timeline_plan


if __name__ == "__main__":
    run_m4_timeline_generation_test()