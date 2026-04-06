from __future__ import annotations

from datetime import datetime
import json
import sys
from pathlib import Path
from typing import Any


RUNNER_DIR = Path(__file__).resolve().parent
if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

import task_v2_highlight_ab_runner as v2_runner


OUTPUT_DIR = v2_runner.PROJECT_ROOT / "output" / "highlight_ab"
REPORT_JSON_PATH = OUTPUT_DIR / "ab_results_three_topics.json"
REPORT_MD_PATH = OUTPUT_DIR / "ab_results_three_topics.md"
PROGRESS_STATUS_PATH = OUTPUT_DIR / "progress_status.json"

TOPICS = [
    {
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
    },
    {
        "slug": "topic2_industrial_precision",
        "title": "高精度自动化设备为什么能提高连续生产稳定性",
        "input_data": {
            "type": "text",
            "content": (
                "高精度自动化设备为什么能提高连续生产稳定性？因为高精度意味着关键动作更一致，误差更小。"
                "自动化意味着流程可以连续执行，减少人工波动。系统一旦具备稳定控制能力，就更容易保持连续生产，"
                "提高效率，并降低停机风险。最终，可靠的设备方案会直接影响产线的稳定产出。"
            ),
        },
    },
    {
        "slug": "topic3_low_cost_advantage",
        "title": "为什么低成本并不一定带来真正的竞争优势",
        "input_data": {
            "type": "text",
            "content": (
                "为什么低成本并不一定带来真正的竞争优势？因为低成本只解决价格问题，却不一定解决用户真正关心的价值。"
                "如果产品缺乏可靠性、效率或者一致性，再低的成本也很难形成长期壁垒。真正的竞争优势，"
                "往往来自持续交付、稳定体验和明确差异化。成本重要，但不是全部。"
            ),
        },
    },
]

TOTAL_CASES = len(TOPICS) * 2


def build_disabled_config() -> dict[str, Any]:
    return {
        "enable_highlight": False,
        "industrial_keywords": [
            "几乎不会命中的词A",
            "几乎不会命中的词B",
        ],
    }


def find_case(cases: list[dict[str, Any]], topic_title: str, variant: str) -> dict[str, Any]:
    for case in cases:
        if case.get("topic") == topic_title and case.get("variant") == variant:
            return case
    return {}


def flatten_highlights(scene_highlights: list[dict[str, Any]]) -> list[str]:
    words: list[str] = []
    for item in scene_highlights:
        raw_items = item.get("highlights", [])
        if not isinstance(raw_items, list):
            continue
        for word in raw_items:
            normalized = str(word or "").strip()
            if normalized:
                words.append(normalized)
    return words


def unique_in_order(words: list[str]) -> list[str]:
    result: list[str] = []
    for word in words:
        if word in result:
            continue
        result.append(word)
    return result


def has_meaningful_highlights(scene_highlights: list[dict[str, Any]]) -> bool:
    return any(item.get("highlights") for item in scene_highlights)


def evaluate_viewpoint(scene_highlights: list[dict[str, Any]]) -> tuple[str, str]:
    words = flatten_highlights(scene_highlights)
    viewpoint_tokens = [
        "利率",
        "资产价格",
        "资产估值",
        "资产估值通常承压",
        "利率预期",
        "高精度",
        "自动化",
        "连续生产",
        "稳定性",
        "稳定产出",
        "竞争优势",
        "长期壁垒",
        "可靠性",
        "差异化",
    ]
    matched = [word for word in words if any(token in word for token in viewpoint_tokens)]
    if len(matched) >= 2:
        return "较好", f"命中核心概念/结论词：{unique_in_order(matched)[:4]}"
    if matched:
        return "一般", f"有主旨词，但密度有限：{unique_in_order(matched)[:3]}"
    return "偏弱", "A组 highlights 里主旨/结论词不足，偏向普通词"


def evaluate_structure(scene_highlights: list[dict[str, Any]]) -> tuple[str, str]:
    words = flatten_highlights(scene_highlights)
    structure_tokens = [
        "上升",
        "下降",
        "承压",
        "提高",
        "降低",
        "不是",
        "而是",
        "导致",
        "改变",
        "影响",
        "当利率上升时",
        "当利率下降时",
    ]
    matched = [word for word in words if any(token in word for token in structure_tokens)]
    if len(matched) >= 2:
        return "较好", f"存在明确结构表达：{unique_in_order(matched)[:4]}"
    if matched:
        return "一般", f"存在少量结构表达：{unique_in_order(matched)[:3]}"
    return "偏弱", "未看到明显的对比/因果/趋势结构词"


def evaluate_information_progression(scene_highlights: list[dict[str, Any]]) -> tuple[str, str]:
    if not scene_highlights:
        return "偏弱", "没有可评估的 scene_highlights"

    midpoint = max(1, len(scene_highlights) // 2)
    front_words = unique_in_order(flatten_highlights(scene_highlights[:midpoint]))
    back_words = unique_in_order(flatten_highlights(scene_highlights[midpoint:]))
    new_back_words = [word for word in back_words if word not in front_words]

    if len(new_back_words) >= 2:
        return "较好", f"后半段出现新信息：{new_back_words[:4]}"
    if len(new_back_words) == 1:
        return "一般", f"后半段有新增信息，但展开有限：{new_back_words[:2]}"
    return "偏弱", "后半段主要重复前半段，信息展开不足"


def evaluate_no_misemphasis(scene_highlights: list[dict[str, Any]]) -> tuple[str, str]:
    words = flatten_highlights(scene_highlights)
    blocked_tokens = ["什么", "为什么", "反过来", "如何", "今天值多少钱"]
    bad_words = [word for word in words if any(token in word for token in blocked_tokens)]
    if bad_words:
        return "偏弱", f"仍存在误强调：{unique_in_order(bad_words)[:4]}"
    if has_meaningful_highlights(scene_highlights):
        return "较好", "未出现明显误强调词或空碎片"
    return "一般", "未见误强调，但 highlights 也较少"


def topic_conclusion(evaluations: dict[str, tuple[str, str]]) -> str:
    good_count = sum(1 for status, _ in evaluations.values() if status == "较好")
    weak_count = sum(1 for status, _ in evaluations.values() if status == "偏弱")

    if good_count >= 3 and weak_count == 0:
        return "好"
    if weak_count >= 2:
        return "不成立"
    return "一般"


def final_conclusion(topic_results: list[dict[str, Any]]) -> str:
    if not topic_results:
        return "进行中（尚无完整主题结果）"
    if len(topic_results) < len(TOPICS):
        return f"进行中（已完成 {len(topic_results)}/{len(TOPICS)} 个主题）"

    topic_conclusions = [item.get("conclusion") for item in topic_results]
    good_count = topic_conclusions.count("好")
    weak_count = topic_conclusions.count("不成立")
    mixed_structure = any(
        item.get("evaluations", {}).get("是否有结构", ("", ""))[0] != "较好"
        for item in topic_results
    )

    if good_count == len(topic_results):
        return "highlight 已稳定成立（可进入产品阶段）"
    if weak_count >= 2:
        return "highlight 在部分主题失效（需要规则调整）"
    if mixed_structure:
        return "highlight 有效果，但不稳定（需要再收一轮）"
    return "highlight 仍然偏形式增强，不是表达增强"


def build_topic_evaluation(
    case_a: dict[str, Any],
    case_b: dict[str, Any],
    topic_key: str,
    topic_title: str,
) -> dict[str, Any]:
    scene_highlights_a = case_a.get("scene_highlights", [])
    evaluations = {
        "是否像观点": evaluate_viewpoint(scene_highlights_a),
        "是否有结构": evaluate_structure(scene_highlights_a),
        "是否信息展开": evaluate_information_progression(scene_highlights_a),
        "是否无误强调": evaluate_no_misemphasis(scene_highlights_a),
    }
    return {
        "topic_key": topic_key,
        "topic": case_a.get("topic") or case_b.get("topic") or topic_title,
        "case_a": case_a,
        "case_b": case_b,
        "evaluations": evaluations,
        "conclusion": topic_conclusion(evaluations),
    }


def format_scene_highlights(scene_highlights: list[dict[str, Any]]) -> str:
    if not scene_highlights:
        return "- 无\n"

    lines = []
    for item in scene_highlights:
        scene_id = item.get("scene_id")
        highlights = item.get("highlights", [])
        lines.append(f"- scene {scene_id}: {json.dumps(highlights, ensure_ascii=False)}")
    return "\n".join(lines) + "\n"


def current_timestamp() -> str:
    return datetime.now().astimezone().isoformat()


def topic_result_path(topic_index: int) -> Path:
    return OUTPUT_DIR / f"topic{topic_index}_result.json"


def build_progress_status(
    *,
    current_topic: str | None,
    current_variant: str | None,
    completed_topics: list[str],
    completed_cases: int,
    status: str,
    error_message: str | None = None,
) -> dict[str, Any]:
    payload = {
        "current_topic": current_topic,
        "current_variant": current_variant,
        "completed_topics": completed_topics,
        "completed_cases": completed_cases,
        "total_cases": TOTAL_CASES,
        "last_update_time": current_timestamp(),
        "status": status,
    }
    if error_message:
        payload["error_message"] = error_message
    return payload


def write_progress_status(payload: dict[str, Any]) -> None:
    v2_runner.write_json(PROGRESS_STATUS_PATH, payload)


def build_completed_topic_results(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    topic_results: list[dict[str, Any]] = []
    for topic_index, topic in enumerate(TOPICS, start=1):
        topic_title = topic["title"]
        case_a = find_case(cases, topic_title, "A")
        case_b = find_case(cases, topic_title, "B")
        if not case_a or not case_b:
            continue
        topic_results.append(
            build_topic_evaluation(case_a, case_b, f"topic{topic_index}", topic_title)
        )
    return topic_results


def build_report_payload(cases: list[dict[str, Any]], progress_status: dict[str, Any]) -> dict[str, Any]:
    topic_results = build_completed_topic_results(cases)
    total_cases = len(cases)
    success_cases = sum(1 for case in cases if case.get("returncode") == 0 and case.get("video_exists"))
    overall_conclusion = final_conclusion(topic_results)

    return {
        "summary": {
            "total_cases_written": total_cases,
            "success_cases": success_cases,
            "completed_topic_count": len(topic_results),
            "total_topic_count": len(TOPICS),
            "overall_conclusion": overall_conclusion,
        },
        "progress": progress_status,
        "topic_results": topic_results,
        "cases": cases,
    }


def build_markdown_report(cases: list[dict[str, Any]], progress_status: dict[str, Any]) -> str:
    topic_results = build_completed_topic_results(cases)
    completed_topic_keys = {item["topic_key"] for item in topic_results}

    total_cases = len(cases)
    success_cases = sum(1 for case in cases if case.get("returncode") == 0 and case.get("video_exists"))
    overall_conclusion = final_conclusion(topic_results)

    lines = [
        "# Highlight A/B Three Topic Evaluation Report",
        "",
        "## 运行摘要",
        "",
        f"- 当前状态: {progress_status.get('status')}",
        f"- 当前主题: {progress_status.get('current_topic')}",
        f"- 当前组别: {progress_status.get('current_variant')}",
        f"- 已完成主题: {json.dumps(progress_status.get('completed_topics', []), ensure_ascii=False)}",
        f"- 已完成 case 数: {progress_status.get('completed_cases')}/{progress_status.get('total_cases')}",
        f"- 最近更新时间: {progress_status.get('last_update_time')}",
        f"- 总 case 数: {total_cases}",
        f"- 成功生成视频的 case 数: {success_cases}",
        f"- 最终总判断: {overall_conclusion}",
        "",
    ]

    for topic_result in topic_results:
        case_a = topic_result["case_a"]
        case_b = topic_result["case_b"]
        evaluations = topic_result["evaluations"]

        lines.extend(
            [
                f"## {topic_result['topic']}",
                "",
                f"- A组 returncode: {case_a.get('returncode')}",
                f"- B组 returncode: {case_b.get('returncode')}",
                f"- A组 video_exists: {case_a.get('video_exists')}",
                f"- B组 video_exists: {case_b.get('video_exists')}",
                "",
                "### A组 scene_highlights",
                format_scene_highlights(case_a.get("scene_highlights", [])),
                "### B组 scene_highlights",
                format_scene_highlights(case_b.get("scene_highlights", [])),
                "### 四项判断",
                f"- 是否像观点: {evaluations['是否像观点'][0]} | {evaluations['是否像观点'][1]}",
                f"- 是否有结构感: {evaluations['是否有结构'][0]} | {evaluations['是否有结构'][1]}",
                f"- 是否信息在展开: {evaluations['是否信息展开'][0]} | {evaluations['是否信息展开'][1]}",
                f"- 是否没有误强调: {evaluations['是否无误强调'][0]} | {evaluations['是否无误强调'][1]}",
                "",
                f"### 单主题结论\n- {topic_result['conclusion']}",
                "",
            ]
        )

    for topic_index, topic in enumerate(TOPICS, start=1):
        topic_key = f"topic{topic_index}"
        if topic_key in completed_topic_keys:
            continue
        lines.extend(
            [
                f"## {topic['title']}",
                "",
                f"- 状态: pending ({topic_key})",
                "",
            ]
        )

    lines.extend(
        [
            "## 最终总判断",
            "",
            f"- {overall_conclusion}",
        ]
    )

    return "\n".join(lines).rstrip() + "\n"


def refresh_reports(cases: list[dict[str, Any]], progress_status: dict[str, Any]) -> None:
    report_payload = build_report_payload(cases, progress_status)
    v2_runner.write_json(REPORT_JSON_PATH, report_payload)
    REPORT_MD_PATH.write_text(build_markdown_report(cases, progress_status), encoding="utf-8")
    print("[TASK_V4] report updated")


def run_topic_cases(
    topic_index: int,
    topic: dict[str, Any],
    normal_config: dict[str, Any],
    disabled_config: dict[str, Any],
    all_results: list[dict[str, Any]],
    completed_topics: list[str],
) -> dict[str, Any]:
    topic_key = f"topic{topic_index}"
    topic_title = topic["title"]

    print(f"[TASK_V4] start {topic_key}")

    for variant, config_payload in (("A", normal_config), ("B", disabled_config)):
        write_progress_status(
            build_progress_status(
                current_topic=topic_key,
                current_variant=variant,
                completed_topics=completed_topics,
                completed_cases=len(all_results),
                status="running",
            )
        )
        log_case_start(topic_index, topic_title, variant)
        result = v2_runner.run_case(topic, variant, config_payload)
        all_results.append(result)
        log_case_done(topic_index, topic_title, variant, result)

    case_a = find_case(all_results, topic_title, "A")
    case_b = find_case(all_results, topic_title, "B")
    topic_result = build_topic_evaluation(case_a, case_b, topic_key, topic_title)
    v2_runner.write_json(topic_result_path(topic_index), topic_result)

    completed_topics.append(topic_key)
    write_progress_status(
        build_progress_status(
            current_topic=topic_key,
            current_variant=None,
            completed_topics=completed_topics,
            completed_cases=len(all_results),
            status="running",
        )
    )

    print(f"[TASK_V4] done {topic_key}")
    return topic_result


def log_case_start(topic_index: int, topic_title: str, variant: str) -> None:
    print(f"[TASK_V4] start topic{topic_index} {variant} | {topic_title}")


def log_case_done(topic_index: int, topic_title: str, variant: str, result: dict[str, Any]) -> None:
    print(
        f"[TASK_V4] done topic{topic_index} {variant} | {topic_title} | "
        f"returncode={result.get('returncode')} | "
        f"video_exists={result.get('video_exists')} | "
        f"final_scene_count={result.get('final_scene_count')}"
    )


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print("[TASK_V4] runner started")

    original_config_text = v2_runner.CONFIG_PATH.read_text(encoding="utf-8")
    normal_config = json.loads(original_config_text)
    disabled_config = build_disabled_config()

    all_results: list[dict[str, Any]] = []
    completed_topics: list[str] = []
    initial_progress = build_progress_status(
        current_topic=None,
        current_variant=None,
        completed_topics=completed_topics,
        completed_cases=0,
        status="running",
    )
    write_progress_status(initial_progress)
    refresh_reports(all_results, initial_progress)

    try:
        for topic_index, topic in enumerate(TOPICS, start=1):
            run_topic_cases(
                topic_index,
                topic,
                normal_config,
                disabled_config,
                all_results,
                completed_topics,
            )

            progress_status = build_progress_status(
                current_topic=f"topic{topic_index}",
                current_variant=None,
                completed_topics=completed_topics,
                completed_cases=len(all_results),
                status="running",
            )
            write_progress_status(progress_status)
            refresh_reports(all_results, progress_status)
    except Exception as error:
        failed_progress = build_progress_status(
            current_topic=None,
            current_variant=None,
            completed_topics=completed_topics,
            completed_cases=len(all_results),
            status="failed",
            error_message=str(error),
        )
        write_progress_status(failed_progress)
        refresh_reports(all_results, failed_progress)
        raise
    finally:
        v2_runner.CONFIG_PATH.write_text(original_config_text, encoding="utf-8")

    final_progress = build_progress_status(
        current_topic=None,
        current_variant=None,
        completed_topics=completed_topics,
        completed_cases=len(all_results),
        status="done",
    )
    write_progress_status(final_progress)
    refresh_reports(all_results, final_progress)

    print(f"[TASK_V4] json_report={REPORT_JSON_PATH}")
    print(f"[TASK_V4] markdown_report={REPORT_MD_PATH}")
    print(f"[TASK_V4] progress_status={PROGRESS_STATUS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())