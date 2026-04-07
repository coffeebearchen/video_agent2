from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Sequence


SUMMARY_PATH = Path(__file__).resolve().parents[2] / "output" / "batch_generation" / "batch_summary.json"
REQUIRED_TOP_LEVEL_FIELDS: Sequence[str] = (
    "mode",
    "total_inputs",
    "total_styles",
    "total_jobs",
    "success_count",
    "failed_count",
    "output_root",
    "generated_at",
    "items",
)
REQUIRED_ITEM_FIELDS: Sequence[str] = (
    "item_id",
    "input_index",
    "input_text",
    "status",
    "styles",
)
REQUIRED_STYLE_FIELDS: Sequence[str] = (
    "style",
    "status",
    "output_dir",
    "preview_path",
    "meta_path",
    "error",
)
VALID_ITEM_STATUSES = {"success", "failed", "partial"}
VALID_STYLE_STATUSES = {"success", "failed"}


def fail(message: str) -> int:
    print(f"[FAIL] {message}")
    print("SUMMARY CONSUMER FAILED")
    return 1


def load_summary(summary_path: Path) -> Dict[str, Any]:
    if not summary_path.is_file():
        raise ValueError(f"summary file not found: {summary_path}")

    try:
        raw_data = json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in summary: {exc}") from exc

    if not isinstance(raw_data, dict):
        raise ValueError("summary top level must be a JSON object")

    return raw_data


def validate_top_level(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    for field_name in REQUIRED_TOP_LEVEL_FIELDS:
        if field_name not in summary:
            raise ValueError(f"missing top-level field: {field_name}")

    items = summary["items"]
    if not isinstance(items, list):
        raise ValueError("top-level field 'items' must be a list")

    return items


def validate_items(items: List[Dict[str, Any]]) -> None:
    for item_index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"item #{item_index} must be an object")

        for field_name in REQUIRED_ITEM_FIELDS:
            if field_name not in item:
                raise ValueError(f"item #{item_index} missing field: {field_name}")

        if item["status"] not in VALID_ITEM_STATUSES:
            raise ValueError(
                f"item {item['item_id']} has invalid status: {item['status']}"
            )

        styles = item["styles"]
        if not isinstance(styles, list):
            raise ValueError(f"item {item['item_id']} field 'styles' must be a list")

        for style_index, style_result in enumerate(styles, start=1):
            if not isinstance(style_result, dict):
                raise ValueError(
                    f"item {item['item_id']} style #{style_index} must be an object"
                )

            for field_name in REQUIRED_STYLE_FIELDS:
                if field_name not in style_result:
                    raise ValueError(
                        f"item {item['item_id']} style #{style_index} missing field: {field_name}"
                    )

            if style_result["status"] not in VALID_STYLE_STATUSES:
                raise ValueError(
                    f"item {item['item_id']} style {style_result['style']} has invalid status: "
                    f"{style_result['status']}"
                )


def validate_counts(summary: Dict[str, Any], items: List[Dict[str, Any]]) -> None:
    total_jobs_from_items = sum(len(item["styles"]) for item in items)
    if total_jobs_from_items != summary["total_jobs"]:
        raise ValueError(
            "total_jobs mismatch: "
            f"items declare {total_jobs_from_items}, summary reports {summary['total_jobs']}"
        )

    success_and_failed = summary["success_count"] + summary["failed_count"]
    if success_and_failed != summary["total_jobs"]:
        raise ValueError(
            "success/failed count mismatch: "
            f"success_count + failed_count = {success_and_failed}, total_jobs = {summary['total_jobs']}"
        )

    if len(items) != summary["total_inputs"]:
        raise ValueError(
            f"total_inputs mismatch: items count is {len(items)}, summary reports {summary['total_inputs']}"
        )


def consume_rows(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for item in summary["items"]:
        for style_result in item["styles"]:
            rows.append(
                {
                    "item_id": item["item_id"],
                    "input_index": item["input_index"],
                    "input_text": item["input_text"],
                    "item_status": item["status"],
                    "style": style_result["style"],
                    "style_status": style_result["status"],
                    "output_dir": style_result["output_dir"],
                    "preview_path": style_result["preview_path"],
                    "meta_path": style_result["meta_path"],
                    "error": style_result["error"],
                }
            )

    return rows


def print_summary_overview(summary: Dict[str, Any]) -> None:
    print("===== BATCH SUMMARY OVERVIEW =====")
    for label in (
        "mode",
        "total_inputs",
        "total_styles",
        "total_jobs",
        "success_count",
        "failed_count",
        "output_root",
        "generated_at",
    ):
        print(f"{label:<13} : {summary[label]}")


def print_consumed_results(rows: List[Dict[str, Any]]) -> None:
    print()
    print("===== CONSUMED RESULTS =====")
    if not rows:
        print("(no style results)")
        return

    for row in rows:
        line = (
            f"[{row['item_id']}] style={row['style']}  status={row['style_status']}  "
            f"preview={row['preview_path']}  meta={row['meta_path']}"
        )
        if row["error"] is not None:
            line += f"  error={row['error']}"
        print(line)


def main() -> int:
    try:
        summary = load_summary(SUMMARY_PATH)
        items = validate_top_level(summary)
        validate_items(items)
        validate_counts(summary, items)
        rows = consume_rows(summary)
    except ValueError as exc:
        return fail(str(exc))

    print_summary_overview(summary)
    print_consumed_results(rows)
    print()
    print("SUMMARY CONSUMER PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())