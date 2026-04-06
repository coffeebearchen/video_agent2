from __future__ import annotations

import json
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUN_MODE_FILE = PROJECT_ROOT / "config" / "run_mode.json"
DEFAULT_RUN_MODE = "full_render"
VALID_RUN_MODES = {"full_render", "preview", "spec_check"}


def get_run_mode() -> str:
    if not RUN_MODE_FILE.exists():
        return DEFAULT_RUN_MODE

    try:
        payload = json.loads(RUN_MODE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_RUN_MODE

    mode = str(payload.get("mode", DEFAULT_RUN_MODE) or DEFAULT_RUN_MODE).strip()
    if mode in VALID_RUN_MODES:
        return mode
    return DEFAULT_RUN_MODE