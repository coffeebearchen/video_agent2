# -*- coding: utf-8 -*-
"""
scene_planner.py

【Scene Planner V1｜冻结版】

职责：
1. 读取 script.json
2. 提取 hook / explanation / conclusion
3. 生成固定 3 个 scene 的骨架结构
4. 写出 scene_plan.json

注意：
- 本模块只处理 SCRIPT → SCENE
- 不做智能分镜
- 不做素材匹配
- 不做时间轴与渲染逻辑
"""

import json
import re

from modules import project_paths
from modules.auto_directives_generator import (
    DEFAULT_STYLE_PRESET,
    generate_auto_directives,
    normalize_style_preset,
)
from modules.config_loader import load_runtime_config
from modules.script_directives_parser import parse_script_directives


SCRIPT_JSON_PATH = getattr(
    project_paths,
    "SCRIPT_JSON_PATH",
    project_paths.get_project_root() / "script.json",
)
SCENE_PLAN_JSON_PATH = getattr(
    project_paths,
    "SCENE_PLAN_JSON_PATH",
    project_paths.get_project_root() / "scene_plan.json",
)
DATA_CURRENT_DIR = getattr(
    project_paths,
    "DATA_CURRENT_DIR",
    project_paths.get_data_current_dir(),
)
CURRENT_SCENE_PLAN_JSON_PATH = getattr(
    project_paths,
    "CURRENT_SCENE_PLAN_JSON_PATH",
    DATA_CURRENT_DIR / "scene_plan.json",
)
HIGHLIGHT_KEYWORDS_CONFIG_PATH = (
    getattr(project_paths, "CONFIG_DIR", project_paths.get_project_root() / "config")
    / "highlight_keywords.json"
)
ensure_core_directories = getattr(
    project_paths,
    "ensure_core_directories",
    project_paths.ensure_standard_directories,
)

MIN_SCENE_FALLBACK_TEXT = "请继续观看。"
PRIMARY_SENTENCE_PATTERN = re.compile(r"[^。！？；.!?;\n]+[。！？；.!?;]?")
SECONDARY_SENTENCE_PATTERN = re.compile(r"[^，、：,:]+[，、：,:]?")
DEFAULT_INDUSTRIAL_HIGHLIGHT_KEYWORDS = [
    "连续生产",
    "自动化",
    "高精度",
    "高效率",
    "低成本",
    "一致性",
    "可靠",
    "稳定",
    "效率",
    "应用广泛",
    "解决方案",
]
GLOBAL_HIGHLIGHT_KEYWORDS = [
    "利率",
    "资产估值",
    "资产价格",
    "估值",
    "现金流",
    "折现方式",
    "折现",
    "利率预期",
    "增长型资产",
    "稳定性",
    "连续生产",
    "高精度",
    "自动化",
    "高效率",
    "低成本",
    "一致性",
    "可靠性",
    "可靠",
    "竞争优势",
    "长期壁垒",
    "稳定产出",
    "停机风险",
]
GLOBAL_HIGHLIGHT_PATTERNS = [
    re.compile(r"资产估值通常承压"),
    re.compile(r"真正的竞争优势"),
    re.compile(r"连续生产稳定性"),
    re.compile(r"长期壁垒"),
    re.compile(r"稳定产出"),
]
STRUCTURE_HIGHLIGHT_PATTERNS = [
    re.compile(r"当利率上升时"),
    re.compile(r"当利率下降时"),
    re.compile(r"利率上升"),
    re.compile(r"利率下降"),
    re.compile(r"上升"),
    re.compile(r"下降"),
    re.compile(r"承压"),
    re.compile(r"提高效率"),
    re.compile(r"降低停机风险"),
    re.compile(r"更容易获得更高定价"),
    re.compile(r"不是[^，。！？；]{1,8}而是[^，。！？；]{1,12}"),
]
DETAIL_HIGHLIGHT_PATTERNS = [
    re.compile(r"\d+(?:\.\d+)?%"),
    re.compile(r"\d+(?:\.\d+)?倍"),
    re.compile(r"\d+(?:\.\d+)?万"),
    re.compile(r"\d+(?:\.\d+)?亿"),
    re.compile(r"\d+(?:\.\d+)?年"),
    re.compile(r"20\d{2}年"),
    re.compile(r"\d+(?:\.\d+)?月"),
    re.compile(r"\d+(?:\.\d+)?天"),
    re.compile(r"\d+(?:\.\d+)?小时"),
]
GENERIC_HIGHLIGHT_STOPWORDS = {
    "我们",
    "你们",
    "他们",
    "这个",
    "这个系统",
    "一种",
    "进行",
    "实现",
    "通过",
    "以及",
    "因为",
    "所以",
    "如果",
    "但是",
    "可以",
    "能够",
    "需要",
    "当前",
    "最后",
    "继续观看",
    "反过来",
    "什么",
    "为什么",
    "如何",
}
HIGHLIGHT_EXACT_BLOCKLIST = {
    "反过来",
    "什么",
    "为什么",
    "如何",
    "今天值多少钱",
    "什么决定资产价格",
    "最后",
    "但是",
    "然而",
    "因为",
    "所以",
}
HIGHLIGHT_SUBSTRING_BLOCKLIST = (
    "什么",
    "为什么",
    "如何",
)
DEFAULT_HIGHLIGHT_CONFIG = {
    "enable_highlight": True,
    "industrial_keywords": DEFAULT_INDUSTRIAL_HIGHLIGHT_KEYWORDS[:],
}
MAX_GLOBAL_HIGHLIGHT_REUSE = 2
_HIGHLIGHT_CONFIG_CACHE = None


def load_script_json():
    """读取 script.json，不存在时抛出清晰中文错误。"""
    print(f"[ScenePlanner] 准备读取 script.json：{SCRIPT_JSON_PATH}")
    if not SCRIPT_JSON_PATH.exists():
        raise FileNotFoundError(f"script.json 不存在：{SCRIPT_JSON_PATH}")

    with open(SCRIPT_JSON_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def load_highlight_config() -> dict:
    global _HIGHLIGHT_CONFIG_CACHE

    if _HIGHLIGHT_CONFIG_CACHE is not None:
        return _HIGHLIGHT_CONFIG_CACHE

    try:
        if HIGHLIGHT_KEYWORDS_CONFIG_PATH.exists():
            with open(HIGHLIGHT_KEYWORDS_CONFIG_PATH, "r", encoding="utf-8") as file:
                data = json.load(file)

            enabled = True
            keywords = []
            if isinstance(data, dict):
                enabled = bool(data.get("enable_highlight", True))
                keywords = data.get("industrial_keywords", [])

            normalized_keywords = dedupe_highlights(keywords, limit=max(2, len(keywords)))
            _HIGHLIGHT_CONFIG_CACHE = {
                "enable_highlight": enabled,
                "industrial_keywords": normalized_keywords,
            }
            print(f"[HIGHLIGHT_CONFIG] loaded_from={HIGHLIGHT_KEYWORDS_CONFIG_PATH}")
            print(f"[HIGHLIGHT_CONFIG] enable_highlight={enabled}")
            print(f"[HIGHLIGHT_CONFIG] keyword_count={len(normalized_keywords)}")
            return _HIGHLIGHT_CONFIG_CACHE
    except Exception as error:
        print(f"[HIGHLIGHT_CONFIG][WARN] load failed: {error}")

    _HIGHLIGHT_CONFIG_CACHE = {
        "enable_highlight": True,
        "industrial_keywords": DEFAULT_INDUSTRIAL_HIGHLIGHT_KEYWORDS[:],
    }
    print("[HIGHLIGHT_CONFIG][FALLBACK] use builtin default keywords")
    print(f"[HIGHLIGHT_CONFIG] enable_highlight={_HIGHLIGHT_CONFIG_CACHE['enable_highlight']}")
    print(f"[HIGHLIGHT_CONFIG] keyword_count={len(_HIGHLIGHT_CONFIG_CACHE['industrial_keywords'])}")
    return _HIGHLIGHT_CONFIG_CACHE


def extract_script_sections(script_data):
    """从 script 数据中提取 hook / explanation / conclusion，缺字段时温和兜底。"""
    hook = str(script_data.get("hook", "") or "").strip()
    explanation = str(script_data.get("explanation", "") or "").strip()
    conclusion = str(script_data.get("conclusion", "") or "").strip()

    cards = script_data.get("cards", [])
    if isinstance(cards, list):
        for card in cards:
            if not isinstance(card, dict):
                continue

            card_type = str(card.get("type", "") or "").strip().lower()
            card_text = str(card.get("text", "") or "").strip()

            if not hook and card_type == "hook":
                hook = card_text
            elif not explanation and card_type == "explanation":
                explanation = card_text
            elif not conclusion and card_type == "conclusion":
                conclusion = card_text

    # 兼容极简 cards 结构：按顺序兜底抽取前三段
    ordered_card_texts = []
    if isinstance(cards, list):
        for card in cards:
            if isinstance(card, dict):
                ordered_card_texts.append(str(card.get("text", "") or "").strip())

    if not hook and len(ordered_card_texts) >= 1:
        hook = ordered_card_texts[0]
    if not explanation and len(ordered_card_texts) >= 2:
        explanation = ordered_card_texts[1]
    if not conclusion and len(ordered_card_texts) >= 3:
        conclusion = ordered_card_texts[2]

    return hook, explanation, conclusion


def extract_script_style_preset(script_data):
    """从 script.json 顶层提取 style preset 原始值。"""
    if not isinstance(script_data, dict):
        return ""

    style_value = script_data.get("style")
    if isinstance(style_value, dict):
        preset = str(style_value.get("preset", "") or "").strip().lower()
        return preset

    return ""


def resolve_style_preset(script_data, runtime_config_result):
    """按 config.json > script.json > default 的顺序解析 style preset。"""
    config_data = runtime_config_result.get("config", {})
    meta_data = runtime_config_result.get("meta", {})
    provided = meta_data.get("provided", {})

    if provided.get("style.preset"):
        preset = str(
            config_data.get("style", {}).get("preset", DEFAULT_STYLE_PRESET)
        ).strip().lower() or DEFAULT_STYLE_PRESET
        return preset, [f"style preset 来源：config.json -> {preset}"]

    script_preset = extract_script_style_preset(script_data)
    if script_preset:
        normalized_preset, fallback_used = normalize_style_preset(script_preset)
        logs = []
        if fallback_used:
            logs.append(f"script.json style.preset 非法，已回退 {DEFAULT_STYLE_PRESET}")
        logs.append(f"style preset 来源：script.json -> {normalized_preset}")
        return normalized_preset, logs

    return DEFAULT_STYLE_PRESET, [f"style preset 未提供，已使用默认值 {DEFAULT_STYLE_PRESET}"]


def clean_scene_text(text) -> str:
    return str(text or "").replace("\r", " ").strip()


def normalize_highlight_word(word: str) -> str:
    normalized = re.sub(r"\s+", "", str(word or ""))
    normalized = re.sub(r"[，。！？；、,.!?;:：]", "", normalized)
    return normalized.strip()


def dedupe_highlights(words: list, limit: int = 2) -> list:
    result = []
    for word in words:
        normalized = normalize_highlight_word(word)
        if not normalized or normalized in result:
            continue
        result.append(normalized)
        if len(result) >= limit:
            break
    return result


def is_valid_highlight_candidate(candidate: str) -> bool:
    normalized = normalize_highlight_word(candidate)
    if not normalized:
        return False
    if normalized in GENERIC_HIGHLIGHT_STOPWORDS:
        return False
    if normalized in HIGHLIGHT_EXACT_BLOCKLIST:
        return False
    if any(token in normalized for token in HIGHLIGHT_SUBSTRING_BLOCKLIST):
        return False
    if len(normalized) < 2:
        return False
    if len(normalized) > 14 and not re.search(r"\d", normalized):
        return False
    return True


def normalize_and_filter_candidates(words: list, limit: int = 10) -> list:
    result = []
    for word in words:
        normalized = normalize_highlight_word(word)
        if not is_valid_highlight_candidate(normalized):
            continue
        if normalized in result:
            continue
        result.append(normalized)
        if len(result) >= limit:
            break
    return result


def extract_pattern_candidates(text: str, patterns: list) -> list:
    candidates = []
    for pattern in patterns:
        for match in pattern.finditer(text):
            candidates.append(match.group(0))
    return normalize_and_filter_candidates(candidates, limit=10)


def build_global_keyword_pool(configured_keywords: list) -> list:
    pool = []
    for word in GLOBAL_HIGHLIGHT_KEYWORDS + list(configured_keywords or []):
        normalized = normalize_highlight_word(word)
        if not normalized or normalized in pool:
            continue
        pool.append(normalized)
    return pool


def extract_global_highlights(text: str, configured_keywords: list, limit: int = 2) -> list:
    candidates = []

    candidates.extend(extract_pattern_candidates(text, GLOBAL_HIGHLIGHT_PATTERNS))

    for keyword in build_global_keyword_pool(configured_keywords):
        if keyword in text:
            candidates.append(keyword)

    return normalize_and_filter_candidates(candidates, limit=limit)


def extract_structure_highlights(text: str, limit: int = 2) -> list:
    candidates = extract_pattern_candidates(text, STRUCTURE_HIGHLIGHT_PATTERNS)
    return normalize_and_filter_candidates(candidates, limit=limit)


def extract_detail_highlights(text: str, limit: int = 2) -> list:
    candidates = extract_pattern_candidates(text, DETAIL_HIGHLIGHT_PATTERNS)
    return normalize_and_filter_candidates(candidates, limit=limit)


def select_highlights_by_priority(
    candidate_groups: list,
    limit: int = 2,
    used_global_keywords: dict | None = None,
) -> list:
    usage_map = used_global_keywords if isinstance(used_global_keywords, dict) else {}

    def can_use_global(word: str) -> bool:
        return usage_map.get(word, 0) < MAX_GLOBAL_HIGHLIGHT_REUSE

    def try_append(word: str, selected: list, is_global: bool) -> bool:
        normalized = normalize_highlight_word(word)
        if not is_valid_highlight_candidate(normalized):
            return False
        if normalized in selected:
            return False
        if is_global and not can_use_global(normalized):
            return False
        selected.append(normalized)
        if is_global:
            usage_map[normalized] = usage_map.get(normalized, 0) + 1
        return True

    def pick_first_valid(group: list, selected: list, is_global: bool) -> None:
        for word in group:
            if try_append(word, selected, is_global=is_global):
                return

    selected = []
    global_candidates = candidate_groups[0] if len(candidate_groups) >= 1 else []
    structure_candidates = candidate_groups[1] if len(candidate_groups) >= 2 else []
    detail_candidates = candidate_groups[2] if len(candidate_groups) >= 3 else []

    pick_first_valid(global_candidates, selected, is_global=True)
    if len(selected) >= limit:
        return selected

    pick_first_valid(structure_candidates, selected, is_global=False)
    if len(selected) >= limit:
        return selected

    for group, is_global in [
        (global_candidates, True),
        (detail_candidates, False),
        (structure_candidates, False),
    ]:
        for word in group:
            if try_append(word, selected, is_global=is_global) and len(selected) >= limit:
                return selected
    return selected


def extract_generic_highlights(text: str, limit: int = 2) -> list:
    candidates = []
    normalized_text = clean_scene_text(text)
    fragments = re.split(r"[，。！？；、,.!?;:：\n]+", normalized_text)

    for fragment in fragments:
        cleaned_fragment = normalize_highlight_word(fragment)
        if not cleaned_fragment:
            continue

        if 2 <= len(cleaned_fragment) <= 8 and cleaned_fragment not in GENERIC_HIGHLIGHT_STOPWORDS:
            candidates.append(cleaned_fragment)
            continue

        sub_parts = re.split(
            r"通过|实现|提升|降低|提供|进行|以及|并且|同时|让|把|对|在|为|与|和|及|将|使|具备|能够|可以",
            cleaned_fragment,
        )
        for sub_part in sub_parts:
            cleaned_sub_part = normalize_highlight_word(sub_part)
            if not cleaned_sub_part:
                continue
            if not (2 <= len(cleaned_sub_part) <= 8):
                continue
            if cleaned_sub_part in GENERIC_HIGHLIGHT_STOPWORDS:
                continue
            candidates.append(cleaned_sub_part)

    return normalize_and_filter_candidates(candidates, limit=limit)


def detect_scene_highlights(text: str, scene_id: int, used_global_keywords: dict | None = None) -> list:
    normalized_text = clean_scene_text(text)
    highlight_config = load_highlight_config()
    if not highlight_config.get("enable_highlight", True):
        print(f"[HIGHLIGHT] scene={scene_id} disabled_by_config")
        return []

    configured_keywords = highlight_config.get("industrial_keywords", [])
    if not normalized_text:
        print(f"[HIGHLIGHT] scene={scene_id} keywords=[]")
        print(f"[HIGHLIGHT][FALLBACK] scene={scene_id} no valid keyword, skip safely")
        return []

    global_candidates = extract_global_highlights(normalized_text, configured_keywords, limit=4)
    structure_candidates = extract_structure_highlights(normalized_text, limit=4)
    detail_candidates = extract_detail_highlights(normalized_text, limit=4)

    highlights = select_highlights_by_priority(
        [global_candidates, structure_candidates, detail_candidates],
        limit=2,
        used_global_keywords=used_global_keywords,
    )
    if not highlights:
        highlights = extract_generic_highlights(normalized_text, limit=2)

    print(
        f"[HIGHLIGHT][LAYERED] scene={scene_id} "
        f"global={global_candidates} structure={structure_candidates} detail={detail_candidates}"
    )
    if used_global_keywords:
        print(f"[HIGHLIGHT][DISTRIBUTION] scene={scene_id} used_global={used_global_keywords}")
    print(f"[HIGHLIGHT] scene={scene_id} keywords={highlights}")
    if not highlights:
        print(f"[HIGHLIGHT][FALLBACK] scene={scene_id} no valid keyword, skip safely")
    return highlights


def split_text_with_pattern(text: str, pattern) -> list:
    return [item.strip() for item in pattern.findall(text or "") if item and item.strip()]


def find_secondary_split_candidate(parts: list) -> int:
    candidate_index = -1
    candidate_length = -1
    for index, part in enumerate(parts):
        if not isinstance(part, str):
            continue
        if not any(mark in part for mark in ["，", "、", "：", ",", ":"]):
            continue
        if len(part) > candidate_length:
            candidate_index = index
            candidate_length = len(part)
    return candidate_index


def merge_parts_evenly(parts: list, target_count: int) -> list:
    if target_count <= 0:
        return []
    if not parts:
        return []
    if len(parts) <= target_count:
        return parts[:]

    merged_parts = []
    total = len(parts)
    start = 0
    for index in range(target_count):
        remaining_parts = total - start
        remaining_slots = target_count - index
        take_count = max(1, remaining_parts // remaining_slots)
        if remaining_parts % remaining_slots != 0:
            take_count += 1
        chunk = parts[start:start + take_count]
        merged_parts.append("".join(chunk).strip())
        start += take_count
    return merged_parts


def split_text_into_parts(text: str, num_parts: int) -> list:
    """
    先按句子拆分，再按逗号类标点做必要的温和二次拆分。
    如果仍不足，则优先复用真实内容，最后才使用最小兜底。
    """
    cleaned_text = clean_scene_text(text)
    if not cleaned_text:
        fallback_parts = [MIN_SCENE_FALLBACK_TEXT] * num_parts
        print(f"[SCENE_SPLIT] sentence_count=0")
        print(f"[SCENE_SPLIT] real_content_part_count=0")
        print(f"[SCENE_SPLIT] fallback_count={num_parts}")
        for index in range(num_parts):
            print(f"[SCENE_SPLIT][FALLBACK] scene {index} 使用最小兜底")
        return fallback_parts

    sentence_parts = split_text_with_pattern(cleaned_text, PRIMARY_SENTENCE_PATTERN)
    if not sentence_parts:
        sentence_parts = [cleaned_text]

    print(f"[SCENE_SPLIT] sentence_count={len(sentence_parts)}")

    working_parts = sentence_parts[:]

    while len(working_parts) < num_parts:
        candidate_index = find_secondary_split_candidate(working_parts)
        if candidate_index < 0:
            break

        source_part = working_parts[candidate_index]
        secondary_parts = split_text_with_pattern(source_part, SECONDARY_SENTENCE_PATTERN)
        secondary_parts = [part for part in secondary_parts if clean_scene_text(part)]
        if len(secondary_parts) <= 1:
            break

        print(f"[SCENE_SPLIT][SECONDARY_SPLIT] source=\"{source_part}\"")
        working_parts = (
            working_parts[:candidate_index]
            + secondary_parts
            + working_parts[candidate_index + 1:]
        )

    if len(working_parts) > num_parts:
        working_parts = merge_parts_evenly(working_parts, num_parts)

    real_parts_before_reuse = [part for part in working_parts if clean_scene_text(part)]
    reuse_source_parts = real_parts_before_reuse[:] or [MIN_SCENE_FALLBACK_TEXT]

    reuse_index = 0
    while len(working_parts) < num_parts and reuse_source_parts:
        reused_part = reuse_source_parts[reuse_index % len(reuse_source_parts)]
        working_parts.append(reused_part)
        reuse_index += 1

    fallback_count = 0
    final_parts = []
    for index, part in enumerate(working_parts[:num_parts]):
        cleaned_part = clean_scene_text(part)
        if not cleaned_part:
            cleaned_part = MIN_SCENE_FALLBACK_TEXT
            fallback_count += 1
            print(f"[SCENE_SPLIT][FALLBACK] scene {index} 使用最小兜底")
        final_parts.append(cleaned_part)

    print(f"[SCENE_SPLIT] real_content_part_count={len(final_parts) - fallback_count}")
    print(f"[SCENE_SPLIT] fallback_count={fallback_count}")
    return final_parts


def build_scene_plan(
    hook,
    explanation,
    conclusion,
    style_preset=DEFAULT_STYLE_PRESET,
    auto_enabled=True,
    max_auto_inserts=2,
    scene_count=None,
):
    """
    构建 scene 的骨架结构。

    - scene_count=None：保持默认自动模式
    - scene_count=3：显式固定 3 个 scene
    - scene_count=5：显式固定 5 个 scene
    """
    scene_specs_base = [
        (0, "intro", "overlay", hook),
        (1, "body", "explain", explanation),
        (2, "outro", "card", conclusion),
    ]

    if scene_count is None:
        print("[SCENE_COUNT] mode=auto")
        scene_specs = scene_specs_base
    elif scene_count == 3:
        print("[SCENE_COUNT] mode=fixed | target=3")
        scene_specs = scene_specs_base
    elif scene_count == 5:
        print("[SCENE_COUNT] mode=fixed | target=5")
        raw_blocks = [
            clean_scene_text(hook),
            clean_scene_text(explanation),
            clean_scene_text(conclusion),
        ]
        raw_blocks = [block for block in raw_blocks if block]
        print(f"[SCENE_SPLIT] raw_block_count={len(raw_blocks)}")
        print("[SCENE_SPLIT] target_scene_count=5")
        fixed_scene_parts = split_text_into_parts("\n".join(raw_blocks), 5)
        scene_specs = [
            (0, "intro", "overlay", fixed_scene_parts[0]),
            (1, "body_1", "explain", fixed_scene_parts[1]),
            (2, "body_2", "explain", fixed_scene_parts[2]),
            (3, "body_3", "explain", fixed_scene_parts[3]),
            (4, "outro", "card", fixed_scene_parts[4]),
        ]
    else:
        raise ValueError(f"scene_count 仅支持 None / 3 / 5，当前值：{scene_count}")

    scene_plan = []
    used_global_keywords = {}
    for scene_id, role, scene_type, raw_text in scene_specs:
        parsed_directives = parse_script_directives(raw_text)
        stats = parsed_directives.get("stats", {})
        ignored_details = parsed_directives.get("ignored_details", [])
        directive_logs = parsed_directives.get("logs", [])
        cleaned_text = parsed_directives.get("text", "")
        visual_inserts = parsed_directives.get("visual_inserts", [])
        expression_enhancements = parsed_directives.get("expression_enhancements", [])

        auto_directives = generate_auto_directives(
            text=cleaned_text,
            existing_visual_inserts=visual_inserts,
            existing_enhancements=expression_enhancements,
            style_preset=style_preset,
            auto_enabled=auto_enabled,
            max_auto_inserts=max_auto_inserts,
        )
        auto_logs = auto_directives.get("logs", [])
        if not visual_inserts:
            visual_inserts = auto_directives.get("visual_inserts", [])
        if not expression_enhancements:
            expression_enhancements = auto_directives.get("expression_enhancements", [])

        scene_item = {
            "scene_id": scene_id,
            "role": role,
            "type": scene_type,
            "text": cleaned_text,
        }

        scene_item["highlights"] = detect_scene_highlights(
            cleaned_text,
            scene_id,
            used_global_keywords=used_global_keywords,
        )

        for log_line in directive_logs:
            print(f"[Directives] scene={scene_id} {log_line}")
        for log_line in auto_logs:
            print(f"[AutoDirectives] scene={scene_id} {log_line}")

        print(
            f"[Directives] scene={scene_id} 检测到 script_directives："
            f"{stats.get('total_directives', 0)} 条"
        )

        if visual_inserts:
            scene_item["visual_inserts"] = visual_inserts
        print(
            f"[Directives] scene={scene_id} 已注入 visual_inserts："
            f"{len(visual_inserts)} 项"
        )

        if expression_enhancements:
            scene_item["expression_enhancements"] = expression_enhancements
        print(
            f"[Directives] scene={scene_id} 已注入 expression_enhancements："
            f"{len(expression_enhancements)} 项"
        )

        ignored_count = stats.get("ignored_directives", 0)
        if ignored_count > 0:
            ignored_reason_summary = "；".join(
                f"{item.get('directive', '')} -> {item.get('reason', '')}"
                for item in ignored_details[:3]
            )
            print(f"[Directives] scene={scene_id} 忽略非法指令：{ignored_count} 条")
            if ignored_reason_summary:
                print(f"[Directives] scene={scene_id} 忽略原因：{ignored_reason_summary}")

        preview_text = cleaned_text[:36]
        if len(cleaned_text) > 36:
            preview_text = f"{preview_text}..."
        print(f"[Directives] scene={scene_id} 清洗后文本：{preview_text}")

        scene_plan.append(scene_item)

    return scene_plan


def save_scene_plan(scene_plan):
    """写出 scene_plan.json，并同时保存下游兼容版本。"""
    print(f"[ScenePlanner] 准备写出 scene_plan.json：{SCENE_PLAN_JSON_PATH}")
    print(f"[ScenePlanner] 准备写出下游兼容 scene_plan.json：{CURRENT_SCENE_PLAN_JSON_PATH}")
    ensure_core_directories()
    DATA_CURRENT_DIR.mkdir(parents=True, exist_ok=True)

    with open(SCENE_PLAN_JSON_PATH, "w", encoding="utf-8") as file:
        json.dump(scene_plan, file, ensure_ascii=False, indent=2)

    downstream_plan = {
        "scenes": scene_plan
    }
    with open(CURRENT_SCENE_PLAN_JSON_PATH, "w", encoding="utf-8") as file:
        json.dump(downstream_plan, file, ensure_ascii=False, indent=2)


def main(scene_count=None):
    print("=" * 60)
    print("开始生成 Scene Planner V1...")
    print("=" * 60)
    print("[ScenePlanner] 开始检查核心目录...")
    ensure_core_directories()
    print(f"[ScenePlanner] 核心目录已就绪：{DATA_CURRENT_DIR}")

    script_data = load_script_json()
    runtime_config_result = load_runtime_config()
    for log_line in runtime_config_result.get("logs", []):
        print(f"[Config] {log_line}")

    hook, explanation, conclusion = extract_script_sections(script_data)
    style_preset, style_logs = resolve_style_preset(script_data, runtime_config_result)
    for log_line in style_logs:
        print(f"[Config] {log_line}")

    runtime_config = runtime_config_result.get("config", {})
    auto_enabled = runtime_config.get("auto_directives", {}).get("enabled", True)
    max_auto_inserts = runtime_config.get("insert_policy", {}).get("max_per_scene", 2)

    scene_plan = build_scene_plan(
        hook,
        explanation,
        conclusion,
        style_preset=style_preset,
        auto_enabled=auto_enabled,
        max_auto_inserts=max_auto_inserts,
        scene_count=scene_count,
    )
    save_scene_plan(scene_plan)

    print(f"已生成 scene_plan.json：{SCENE_PLAN_JSON_PATH}")
    print(f"已生成下游兼容 scene_plan.json：{CURRENT_SCENE_PLAN_JSON_PATH}")
    print(f"[SCENE_COUNT] final_scene_count={len(scene_plan)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
