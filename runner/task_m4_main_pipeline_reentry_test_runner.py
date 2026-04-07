# -*- coding: utf-8 -*-
"""
Isolated main pipeline re-entry verification runner.

职责：
1. 读取 timeline_plan.json
2. 调用 main_pipeline_reentry_adapter
3. 解析旧主链真实入口
4. 在隔离 runner 中临时回接旧 video_engine
5. 结构化记录成功或失败，并恢复现场
"""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
from typing import Any, Dict, Optional, Tuple


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from modules import project_paths
from modules.content_processor.main_pipeline_reentry_adapter import build_main_pipeline_reentry_input


DATA_CURRENT_DIR = Path(project_paths.get_data_current_dir())
TIMELINE_PLAN_PATH = DATA_CURRENT_DIR / "timeline_plan.json"
LEGACY_SCENE_ASSETS_PATH = DATA_CURRENT_DIR / "scene_assets.json"
SCENE_ASSETS_BACKUP_PATH = DATA_CURRENT_DIR / "scene_assets.m4_reentry_backup.json"
RESULT_PATH = DATA_CURRENT_DIR / "main_pipeline_reentry_result.json"
OUTPUT_VIDEO_PATH = PROJECT_ROOT / "output" / "video.mp4"


def _write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def _load_json_object(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object expected: {path}")
    return payload


def _resolve_scene_clip_scheduler_entry() -> Optional[str]:
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

        entry = getattr(module, attr_name, None)
        if callable(entry):
            module_path = str(getattr(module, "__file__", "") or "")
            if module_path.endswith("modules\\scene_clip_scheduler.py"):
                return None
            return f"{module_name}.{attr_name}"
    return None


def _resolve_video_engine_entry() -> Tuple[Optional[Any], Optional[str]]:
    candidate_imports = [
        ("modules.video_engine", "main"),
        ("video_engine", "main"),
    ]

    for module_name, attr_name in candidate_imports:
        try:
            module = __import__(module_name, fromlist=[attr_name])
        except Exception:
            continue

        entry = getattr(module, attr_name, None)
        if callable(entry):
            return entry, f"{module_name}.{attr_name}"
    return None, None


def _resolve_overlay_renderer_entry() -> Optional[str]:
    candidate_imports = [
        ("modules.overlay_renderer", "apply_scene_expression_overlay"),
        ("overlay_renderer", "apply_scene_expression_overlay"),
    ]

    for module_name, attr_name in candidate_imports:
        try:
            module = __import__(module_name, fromlist=[attr_name])
        except Exception:
            continue

        entry = getattr(module, attr_name, None)
        if callable(entry):
            return f"{module_name}.{attr_name}"
    return None


def _write_legacy_scene_assets(scene_assets: Any) -> None:
    payload = {"scene_assets": scene_assets if isinstance(scene_assets, list) else []}
    _write_json(LEGACY_SCENE_ASSETS_PATH, payload)


def _result_base() -> Dict[str, Any]:
    return {
        "ok": False,
        "stage": "main_pipeline_reentry",
        "error_type": "",
        "error_message": "",
        "resolved_old_entry": False,
        "used_input_source": "timeline_plan",
    }


def run_m4_main_pipeline_reentry_test() -> Dict[str, Any]:
    had_original_scene_assets = LEGACY_SCENE_ASSETS_PATH.exists()
    if had_original_scene_assets:
        shutil.copyfile(LEGACY_SCENE_ASSETS_PATH, SCENE_ASSETS_BACKUP_PATH)

    result = _result_base()

    try:
        print("[M4-REENTRY] start")
        print("[M4-REENTRY] input_source=timeline_plan")

        timeline_plan = _load_json_object(TIMELINE_PLAN_PATH)
        reentry_input = build_main_pipeline_reentry_input(timeline_plan, input_source="timeline_plan")
        _write_legacy_scene_assets(reentry_input.get("scene_assets", []))

        print("[M4-REENTRY] resolving old main pipeline entry")
        scene_clip_scheduler_entry = _resolve_scene_clip_scheduler_entry()
        overlay_renderer_entry = _resolve_overlay_renderer_entry()
        video_engine_callable, video_engine_entry = _resolve_video_engine_entry()

        if not video_engine_callable or not video_engine_entry:
            print("[M4-REENTRY] old main pipeline callable not found")
            result.update(
                {
                    "error_type": "entry_not_found",
                    "error_message": "old main pipeline callable not found",
                    "resolved_old_entry": False,
                    "called_entry": "",
                    "scene_clip_scheduler_entry": scene_clip_scheduler_entry or "",
                    "video_engine_entry": "",
                    "overlay_renderer_entry": overlay_renderer_entry or "",
                }
            )
            return result

        print(f"[M4-REENTRY] old entry resolved: {video_engine_entry}")
        result.update(
            {
                "resolved_old_entry": True,
                "called_entry": video_engine_entry,
                "scene_clip_scheduler_entry": scene_clip_scheduler_entry or "",
                "video_engine_entry": video_engine_entry,
                "overlay_renderer_entry": overlay_renderer_entry or "",
                "legacy_scene_assets_path": str(LEGACY_SCENE_ASSETS_PATH),
                "main_pipeline_reentry_input_path": str(DATA_CURRENT_DIR / "main_pipeline_reentry_input.json"),
            }
        )

        print("[M4-REENTRY] calling old pipeline entry")
        old_return_value = video_engine_callable()
        print("[M4-REENTRY] returned")

        result_type = "other"
        if isinstance(old_return_value, dict):
            result_type = "dict"
        elif isinstance(old_return_value, (str, Path)):
            result_type = "path"

        result.update(
            {
                "ok": True,
                "error_type": "",
                "error_message": "",
                "result_type": result_type,
                "return_value": str(old_return_value) if old_return_value is not None else "",
                "output_video_exists": OUTPUT_VIDEO_PATH.exists(),
                "output_video": str(OUTPUT_VIDEO_PATH) if OUTPUT_VIDEO_PATH.exists() else "",
            }
        )
        return result

    except Exception as error:
        message = str(error)
        print(f"[M4-REENTRY] failed: {message}")
        result.update(
            {
                "ok": False,
                "error_type": type(error).__name__,
                "error_message": message,
            }
        )
        return result
    finally:
        if had_original_scene_assets and SCENE_ASSETS_BACKUP_PATH.exists():
            shutil.copyfile(SCENE_ASSETS_BACKUP_PATH, LEGACY_SCENE_ASSETS_PATH)
            SCENE_ASSETS_BACKUP_PATH.unlink()
        elif LEGACY_SCENE_ASSETS_PATH.exists():
            LEGACY_SCENE_ASSETS_PATH.unlink()

        _write_json(RESULT_PATH, result)
        print("[M4-REENTRY] done")


if __name__ == "__main__":
    final_result = run_m4_main_pipeline_reentry_test()
    print(json.dumps(final_result, ensure_ascii=False, indent=2, default=str))