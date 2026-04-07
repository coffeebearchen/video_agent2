from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, DefaultDict, Dict, List, Sequence


SUMMARY_PATH = Path(__file__).resolve().parents[2] / "output" / "batch_generation" / "batch_summary.json"
REQUIRED_TOP_LEVEL_FIELDS: Sequence[str] = (
    "mode",
    "total_inputs",
    "total_styles",
    "total_jobs",
    "success_count",
    "failed_count",
    "items",
)
REQUIRED_ITEM_FIELDS: Sequence[str] = (
    "item_id",
    "status",
    "styles",
)
REQUIRED_STYLE_FIELDS: Sequence[str] = (
    "style",
    "status",
)
VALID_ITEM_STATUSES = {"success", "failed", "partial"}
VALID_STYLE_STATUSES = {"success", "failed"}


def fail(message: str) -> int:
    print(f"[FAIL] {message}")
    print("SUMMARY STATS FAILED")
    return 1


def load_summary(summary_path: Path) -> Dict[str, Any]:
    if not summary_path.is_file():
        raise ValueError(f"summary file not found: {summary_path}")

    try:
        data = json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in summary: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("summary top level must be a JSON object")

    return data


def validate_min_schema(summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    for field_name in REQUIRED_TOP_LEVEL_FIELDS:
        if field_name not in summary:
            raise ValueError(f"missing top-level field: {field_name}")

    items = summary["items"]
    if not isinstance(items, list):
        raise ValueError("top-level field 'items' must be a list")

    for item_index, item in enumerate(items, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"item #{item_index} must be an object")

        for field_name in REQUIRED_ITEM_FIELDS:
            if field_name not in item:
                raise ValueError(f"item #{item_index} missing field: {field_name}")

        if item["status"] not in VALID_ITEM_STATUSES:
            raise ValueError(f"item {item['item_id']} has invalid status: {item['status']}")

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

    return items


def validate_counts(
    summary: Dict[str, Any],
    items: List[Dict[str, Any]],
    style_stats: Dict[str, Dict[str, int]],
) -> None:
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

    style_job_total = sum(entry["job_count"] for entry in style_stats.values())
    if style_job_total != summary["total_jobs"]:
        raise ValueError(
            f"style job total mismatch: style stats sum to {style_job_total}, total_jobs = {summary['total_jobs']}"
        )

    style_success_total = sum(entry["success_count"] for entry in style_stats.values())
    if style_success_total != summary["success_count"]:
        raise ValueError(
            "style success total mismatch: "
            f"style stats sum to {style_success_total}, success_count = {summary['success_count']}"
        )

    style_failed_total = sum(entry["failed_count"] for entry in style_stats.values())
    if style_failed_total != summary["failed_count"]:
        raise ValueError(
            "style failed total mismatch: "
            f"style stats sum to {style_failed_total}, failed_count = {summary['failed_count']}"
        )


def build_style_stats(summary: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
    stats: DefaultDict[str, Dict[str, int]] = defaultdict(
        lambda: {"job_count": 0, "success_count": 0, "failed_count": 0}
    )

    for item in summary["items"]:
        item_status = item["status"]
        for style_result in item["styles"]:
            style_name = style_result["style"]
            style_status = style_result["status"]
            stats[style_name]["job_count"] += 1
            if style_status == "success":
                stats[style_name]["success_count"] += 1
            else:
                stats[style_name]["failed_count"] += 1

    return dict(stats)


def build_item_status_stats(items: List[Dict[str, Any]]) -> Dict[str, int]:
    stats = {"success": 0, "partial": 0, "failed": 0}

    for item in items:
        stats[item["status"]] += 1

    return stats


def format_percent(numerator: int, denominator: int) -> str:
    if denominator <= 0:
        return "0.00%"
    return f"{(numerator / denominator) * 100:.2f}%"


def print_overview(summary: Dict[str, Any]) -> None:
    print("===== BATCH STATS OVERVIEW =====")
    print(f"{'mode':<20} : {summary['mode']}")
    print(f"{'total_inputs':<20} : {summary['total_inputs']}")
    print(f"{'total_styles':<20} : {summary['total_styles']}")
    print(f"{'total_jobs':<20} : {summary['total_jobs']}")
    print(f"{'success_count':<20} : {summary['success_count']}")
    print(f"{'failed_count':<20} : {summary['failed_count']}")
    print(
        f"{'overall_success_rate':<20} : "
        f"{format_percent(summary['success_count'], summary['total_jobs'])}"
    )


def print_style_stats(style_stats: Dict[str, Dict[str, int]]) -> None:
    print()
    print("===== STYLE STATS =====")
    if not style_stats:
        print("(no style stats)")
        return

    for style_name in sorted(style_stats):
        entry = style_stats[style_name]
        print(
            f"{style_name:<16} "
            f"jobs={entry['job_count']}  "
            f"success={entry['success_count']}  "
            f"failed={entry['failed_count']}  "
            f"success_rate={format_percent(entry['success_count'], entry['job_count'])}"
        )


def print_item_status_stats(item_status_stats: Dict[str, int]) -> None:
    print()
    print("===== ITEM STATUS STATS =====")
    print(f"{'success':<7}: {item_status_stats['success']}")
    print(f"{'partial':<7}: {item_status_stats['partial']}")
    print(f"{'failed':<7}: {item_status_stats['failed']}")


def main() -> int:
    try:
        summary = load_summary(SUMMARY_PATH)
        items = validate_min_schema(summary)
        style_stats = build_style_stats(summary)
        item_status_stats = build_item_status_stats(items)
        validate_counts(summary, items, style_stats)
    except ValueError as exc:
        return fail(str(exc))

    print_overview(summary)
    print_style_stats(style_stats)
    print_item_status_stats(item_status_stats)
    print()
    print("SUMMARY STATS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())