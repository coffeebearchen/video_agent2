from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import run_pipeline_user


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one pipeline case from a UTF-8 input JSON file.",
    )
    parser.add_argument(
        "--input-file",
        required=True,
        help="Path to a UTF-8 JSON file containing the standard input payload.",
    )
    parser.add_argument(
        "--scene-count",
        type=int,
        default=5,
        help="Scene count forwarded to run_pipeline_user.run_pipeline.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_file = Path(args.input_file)
    if not input_file.exists():
        print(f"[CASE_RUNNER][ERROR] input file not found: {input_file}", file=sys.stderr)
        return 2

    try:
        input_data = json.loads(input_file.read_text(encoding="utf-8"))
        video_path = run_pipeline_user.run_pipeline(input_data, scene_count=args.scene_count)
    except Exception as error:  # pragma: no cover - runner should preserve tracebacks
        print(f"[CASE_RUNNER][ERROR] {error}", file=sys.stderr)
        traceback.print_exc(file=sys.stderr)
        return 1

    print(f"[CASE_RUNNER] completed | video={video_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())