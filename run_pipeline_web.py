# -*- coding: utf-8 -*-
"""
run_pipeline_web.py

【主链总调度器】

作用：
1. 接收 URL 输入（优先读取 input.json，否则手动输入）
2. 生成唯一 capture_path
3. 写入 current_capture_path.txt（唯一来源）
4. 调度所有模块执行

注意：
- 这是唯一写 capture_path 的地方
- 下游模块禁止再写
- 当前主链仅支持 type="url"，其他类型会报错退出
"""

import json
import subprocess
from datetime import datetime
from pathlib import Path
import re

from PIL import Image, ImageDraw, ImageFont
from modules import project_paths

PROJECT_ROOT = getattr(
    project_paths,
    "PROJECT_ROOT",
    project_paths.get_project_root(),
)
ASSETS_DIR = getattr(
    project_paths,
    "ASSETS_DIR",
    project_paths.get_assets_dir(),
)
DATA_CURRENT_DIR = getattr(
    project_paths,
    "DATA_CURRENT_DIR",
    project_paths.get_data_current_dir(),
)
OUTPUT_DIR = getattr(
    project_paths,
    "OUTPUT_DIR",
    project_paths.get_project_root() / "output",
)
IMAGES_DIR = getattr(
    project_paths,
    "IMAGES_DIR",
    project_paths.get_project_root() / "images",
)
FONTS_DIR = getattr(
    project_paths,
    "FONTS_DIR",
    project_paths.get_project_root() / "fonts",
)
INPUT_JSON_FILE = getattr(
    project_paths,
    "INPUT_JSON_PATH",
    project_paths.get_project_root() / "input.json",
)
CURRENT_CAPTURE_PATH_FILE = getattr(
    project_paths,
    "CURRENT_CAPTURE_PATH_FILE",
    project_paths.get_project_root() / "current_capture_path.txt",
)
WEB_CAPTURE_DIR = getattr(
    project_paths,
    "WEB_CAPTURE_DIR",
    getattr(project_paths, "ASSETS_DIR", project_paths.get_assets_dir()) / "web_capture",
)
SCRIPT_FILE = getattr(
    project_paths,
    "SCRIPT_JSON_PATH",
    project_paths.get_project_root() / "script.json",
)
DATA_SCRIPT_FILE = getattr(
    project_paths,
    "CURRENT_SCRIPT_JSON_PATH",
    project_paths.get_data_current_dir() / "script.json",
)
SCENE_PLAN_FILE = getattr(
    project_paths,
    "CURRENT_SCENE_PLAN_JSON_PATH",
    project_paths.get_data_current_dir() / "scene_plan.json",
)
SCENE_ASSETS_FILE = getattr(
    project_paths,
    "SCENE_ASSETS_JSON_PATH",
    project_paths.get_data_current_dir() / "scene_assets.json",
)
OUTPUT_VIDEO_FILE = getattr(
    project_paths,
    "OUTPUT_VIDEO_FILE",
    OUTPUT_DIR / "video.mp4",
)
FLAT_IMAGE_DIR = getattr(
    project_paths,
    "FLAT_IMAGE_DIR",
    IMAGES_DIR / "flat",
)
TEXT_CARD_SIZE = (1080, 1350)
TEXT_CARD_TYPES = ["hook", "concept", "explanation", "analogy", "conclusion"]
TEXT_CARD_FONT_CANDIDATES = [
    FONTS_DIR / "SourceHanSansSC-Regular.otf",
    FONTS_DIR / "SourceHanSansCN-Bold.otf",
    Path("C:/Windows/Fonts/msyh.ttc"),
    Path("C:/Windows/Fonts/simhei.ttf"),
]


def safe_name(text: str):
    text = re.sub(r"[\\/:*?\"<>|]", "_", text)
    text = re.sub(r"\s+", "_", text)
    return text[:60]


def ensure_pipeline_directories():
    DATA_CURRENT_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    WEB_CAPTURE_DIR.mkdir(parents=True, exist_ok=True)


def log_pipeline_paths():
    print(f"[PIPELINE] 当前项目根路径：{PROJECT_ROOT}")
    print(f"[PIPELINE] 当前数据目录：{DATA_CURRENT_DIR}")
    print(f"[PIPELINE] 当前输出目录：{OUTPUT_DIR}")
    print(f"[PIPELINE] 当前 capture 目录：{WEB_CAPTURE_DIR}")
    print(f"[PIPELINE] 当前 script 路径：{SCRIPT_FILE}")
    print(f"[PIPELINE] 当前 scene_plan 路径：{SCENE_PLAN_FILE}")
    print(f"[PIPELINE] 当前 scene_assets 路径：{SCENE_ASSETS_FILE}")
    print(f"[PIPELINE] 当前输出视频路径：{OUTPUT_VIDEO_FILE}")


def assert_path_exists(path: Path, label: str):
    if not path.exists():
        raise RuntimeError(f"[PIPELINE] {label} 不存在：{path}")


def assert_nonempty_file(path: Path, label: str):
    assert_path_exists(path, label)
    if path.stat().st_size <= 0:
        raise RuntimeError(f"[PIPELINE] {label} 文件大小为 0：{path}")


def generate_capture_path(url: str):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = safe_name(url.replace("https://", "").replace("http://", ""))
    path = WEB_CAPTURE_DIR / f"{timestamp}_{safe}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_capture_path(path: Path):
    if not CURRENT_CAPTURE_PATH_FILE.exists():
        print(f"[PIPELINE][WARN] current_capture_path.txt 不存在，将创建：{CURRENT_CAPTURE_PATH_FILE}")
    CURRENT_CAPTURE_PATH_FILE.write_text(str(path), encoding="utf-8")
    print(f"[CAPTURE] 主链生成 capture_path：{path}")
    print(f"[PIPELINE] 当前 capture_path 文件：{CURRENT_CAPTURE_PATH_FILE}")


def run_step(title, cmd, pipeline_label=None):
    print(f"\n{title}")
    if pipeline_label:
        print(f"[PIPELINE] 开始执行 {pipeline_label}")
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        raise RuntimeError(f"执行失败：{' '.join(cmd)}")


def load_url_input():
    """
    加载 URL 输入，优先读取 input.json，否则手动输入
    
    逻辑：
    1. 如果存在 input.json，使用 input_handler 读取并验证
    2. 如果不存在 input.json，提示手动输入 URL
    3. 如果 type != "url"，报错退出（当前只支持 URL 模式）
    
    返回：
        {"type": "url" | "text", "content": "..."}
    
    异常：
        ValueError: type 不是 url，或格式校验失败
    """
    input_json_path = INPUT_JSON_FILE
    
    # ===== 尝试读取 input.json =====
    if input_json_path.exists():
        try:
            from input_handler import InputFileHandler
            
            handler = InputFileHandler(str(input_json_path))
            data = handler.read_from_file()

            input_type = str(data.get("type", "")).strip().lower()
            content = str(data.get("content", "")).strip()

            if input_type not in {"url", "text"}:
                raise ValueError(
                    f"[ERROR] input.json 中 type 仅支持 'url' 或 'text'，当前为：{data.get('type')}"
                )

            if not content:
                raise ValueError("[ERROR] input.json 中 content 不能为空")

            if input_type == "url":
                print(f"[INPUT] 从 input.json 读取 URL：{content}")
            else:
                print(f"[INPUT] 从 input.json 读取 TEXT，长度：{len(content)}")

            return {
                "type": input_type,
                "content": content,
            }
            
        except ValueError:
            # 校验失败，直接抛出（不自动降级到手动输入）
            raise
        except Exception as e:
            # input.json 存在但格式有问题，明确报错
            raise ValueError(
                f"[ERROR] 读取 input.json 失败：{str(e)}"
            )
    
    # ===== 无 input.json，手动输入 =====
    print(f"[PIPELINE][WARN] input.json 不存在，切换手动输入模式：{input_json_path}")
    url = input("请输入网页 URL：").strip()
    if not url:
        raise ValueError("URL 不能为空")
    
    return {
        "type": "url",
        "content": url,
    }


def clean_text_segment(text: str):
    return re.sub(r"\s+", " ", str(text or "").strip())


def is_short_text_segment(text: str, min_length: int = 18):
    return len(clean_text_segment(text)) < min_length


def should_merge_with_previous(text: str):
    cleaned = clean_text_segment(text)
    if not cleaned:
        return False

    weak_prefixes = (
        "但",
        "但是",
        "不过",
        "而",
        "而且",
        "并且",
        "同时",
        "另外",
        "此外",
        "因此",
        "所以",
        "因为",
        "由于",
        "如果",
        "其中",
        "尤其",
        "并",
        "且",
        "也",
        "则",
    )
    weak_suffixes = ("中", "后", "时", "下", "上", "前", "里")

    return (
        is_short_text_segment(cleaned, min_length=16)
        or cleaned.startswith(weak_prefixes)
        or cleaned.endswith(weak_suffixes)
    )


def split_text_into_sentences(text: str):
    normalized_text = str(text or "").strip()
    if not normalized_text:
        return []

    parts = re.split(r"(?<=[。！？!?；;])|\n+", normalized_text)
    sentences = []

    for part in parts:
        cleaned = clean_text_segment(part)
        if cleaned:
            sentences.append(cleaned)

    return sentences


def merge_short_sentence_segments(parts):
    cleaned_parts = [clean_text_segment(part) for part in parts if clean_text_segment(part)]
    if len(cleaned_parts) <= 1:
        return cleaned_parts

    merged_parts = []

    for part in cleaned_parts:
        if not merged_parts:
            merged_parts.append(part)
            continue

        if should_merge_with_previous(part):
            merged_parts[-1] = f"{merged_parts[-1]}{part}"
            continue

        if is_short_text_segment(merged_parts[-1], min_length=14):
            merged_parts[-1] = f"{merged_parts[-1]}{part}"
            continue

        merged_parts.append(part)

    if len(merged_parts) >= 2 and is_short_text_segment(merged_parts[-1], min_length=16):
        merged_parts[-2] = f"{merged_parts[-2]}{merged_parts[-1]}"
        merged_parts.pop()

    return merged_parts


def merge_segments_to_max_count(parts, max_segments=3, joiner=""):
    cleaned_parts = [clean_text_segment(part) for part in parts if clean_text_segment(part)]
    if not cleaned_parts:
        return []

    if len(cleaned_parts) <= max_segments:
        return cleaned_parts

    lengths = [len(part) for part in cleaned_parts]
    prefix_lengths = [0]
    for length in lengths:
        prefix_lengths.append(prefix_lengths[-1] + length)

    total_length = prefix_lengths[-1]
    target_length = total_length / max_segments
    best_score = None
    best_groups = None

    for first_cut in range(1, len(cleaned_parts) - 1):
        for second_cut in range(first_cut + 1, len(cleaned_parts)):
            groups = [
                cleaned_parts[:first_cut],
                cleaned_parts[first_cut:second_cut],
                cleaned_parts[second_cut:],
            ]
            group_lengths = [
                prefix_lengths[first_cut] - prefix_lengths[0],
                prefix_lengths[second_cut] - prefix_lengths[first_cut],
                prefix_lengths[len(cleaned_parts)] - prefix_lengths[second_cut],
            ]

            score = sum(abs(group_length - target_length) for group_length in group_lengths)
            score += max(0, 12 - min(group_lengths)) * 3

            if best_score is None or score < best_score:
                best_score = score
                best_groups = groups

    if not best_groups:
        return cleaned_parts[:max_segments]

    merged_segments = []
    for group in best_groups:
        merged_segments.append(joiner.join(group).strip())

    return [segment for segment in merged_segments if segment]


def split_text_without_sentence_delimiters(text: str):
    normalized_text = clean_text_segment(text)
    if not normalized_text:
        return []

    minor_parts = [
        clean_text_segment(part)
        for part in re.split(r"[，,：:、]+", normalized_text)
        if clean_text_segment(part)
    ]

    if len(minor_parts) > 1:
        merged_minor_parts = merge_short_sentence_segments(minor_parts)
        if len(merged_minor_parts) <= 3:
            return merged_minor_parts
        return merge_segments_to_max_count(merged_minor_parts, max_segments=3, joiner="，")

    chunk_size = max(1, (len(normalized_text) + 2) // 3)
    chunks = [
        clean_text_segment(normalized_text[index:index + chunk_size])
        for index in range(0, len(normalized_text), chunk_size)
    ]
    return merge_segments_to_max_count(chunks, max_segments=3, joiner="")


def split_text_into_cards(text: str):
    raw_text = str(text or "").strip()
    if not raw_text:
        raise ValueError("[ERROR] TEXT 模式输入不能为空")

    sentence_segments = merge_short_sentence_segments(split_text_into_sentences(raw_text))

    if sentence_segments:
        if len(sentence_segments) <= 3:
            return sentence_segments
        return merge_segments_to_max_count(sentence_segments, max_segments=3, joiner="")

    return split_text_without_sentence_delimiters(raw_text)


def choose_text_card_types(segments):
    segment_count = len(segments)
    if segment_count <= 0:
        return []

    if segment_count == 1:
        return ["explanation"]

    if segment_count == 2:
        last_text = clean_text_segment(segments[-1])
        conclusion_markers = (
            "因此",
            "所以",
            "这意味着",
            "这也意味着",
            "这会",
            "最终",
            "总的来看",
            "总之",
            "需要注意",
            "背后",
            "其实",
        )
        if any(marker in last_text for marker in conclusion_markers):
            return ["hook", "conclusion"]
        return ["hook", "explanation"]

    return ["hook", "explanation", "conclusion"]


def build_hook_question(text: str):
    cleaned = clean_text_segment(text)
    if not cleaned:
        return ""

    lead = re.split(r"[，,。！？!?]", cleaned, maxsplit=1)[0].strip()
    if not lead:
        return ""

    if "上涨" in lead:
        topic = lead.replace("上涨", "").strip()
        if topic:
            return f"{topic}为什么又涨了？"

    if "下跌" in lead:
        topic = lead.replace("下跌", "").strip()
        if topic:
            return f"{topic}为什么又跌了？"

    if "转向" in cleaned:
        return "市场为什么开始转向了？"

    if "变化" in cleaned:
        return "这背后到底发生了什么变化？"

    return "这背后到底发生了什么？"


def enhance_hook_text(text: str):
    cleaned = clean_text_segment(text)
    if not cleaned:
        return cleaned

    if cleaned.startswith(("很多人以为", "表面上看", "为什么", "这背后")):
        return cleaned

    if "？" in cleaned or "?" in cleaned:
        return cleaned

    if "并不只是" in cleaned:
        prefix, suffix = cleaned.split("并不只是", 1)
        prefix = prefix.rstrip("，, ")
        suffix = suffix.lstrip()

        if "，而是" in suffix:
            assumed_part, actual_part = suffix.split("，而是", 1)
            return f"很多人以为{prefix}只是{assumed_part}，但其实不是，而是{actual_part}"

        return f"很多人以为{prefix}只是{suffix}"

    if any(keyword in cleaned for keyword in ("表面上是", "上涨", "变化", "转向")):
        question = build_hook_question(cleaned)
        if question:
            return f"{question}{cleaned}"

    return cleaned


def generate_script_from_text(text: str):
    from script_enhancer import enhance_speech_rhythm

    segments = split_text_into_cards(text)
    card_types = choose_text_card_types(segments)
    cards = []

    for index, segment in enumerate(segments):
        card_type = card_types[min(index, len(card_types) - 1)]
        cards.append({
            "type": card_type,
            "text": segment,
        })

    if cards:
        cards[0]["text"] = enhance_hook_text(cards[0]["text"])

    for card in cards:
        card["text"] = enhance_speech_rhythm(card["text"])

    script_data = {
        "cards": cards,
    }

    DATA_CURRENT_DIR.mkdir(parents=True, exist_ok=True)

    SCRIPT_FILE.write_text(
        json.dumps(script_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    DATA_SCRIPT_FILE.write_text(
        json.dumps(script_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"[OK] TEXT 模式 script.json 已生成：{SCRIPT_FILE}")
    print(f"[OK] TEXT 模式当前 script.json 已生成：{DATA_SCRIPT_FILE}")
    return script_data


def load_text_card_font(font_size: int):
    for font_path in TEXT_CARD_FONT_CANDIDATES:
        if font_path.exists():
            try:
                return ImageFont.truetype(str(font_path), font_size)
            except Exception:
                continue
    return ImageFont.load_default()


def wrap_text_for_card(draw, text, font, max_width):
    lines = []
    paragraphs = str(text or "").split("\n")

    for paragraph_index, paragraph in enumerate(paragraphs):
        if paragraph == "":
            lines.append("")
            continue

        current_line = ""
        for char in paragraph:
            candidate = f"{current_line}{char}"
            if draw.textlength(candidate, font=font) <= max_width:
                current_line = candidate
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char

        if current_line:
            lines.append(current_line)

        if paragraph_index < len(paragraphs) - 1 and paragraph != "":
            next_paragraph = paragraphs[paragraph_index + 1]
            if next_paragraph == "":
                continue

    return lines or [str(text or "")]


def generate_text_cards(cards):
    FLAT_IMAGE_DIR.mkdir(parents=True, exist_ok=True)

    for old_card in FLAT_IMAGE_DIR.glob("card_*.*"):
        if old_card.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            old_card.unlink(missing_ok=True)

    width, height = TEXT_CARD_SIZE
    background_color = (245, 239, 226)
    title_color = (102, 75, 46)
    text_color = (34, 34, 34)
    accent_color = (198, 120, 53)

    for index, card in enumerate(cards):
        image = Image.new("RGB", (width, height), background_color)
        draw = ImageDraw.Draw(image)

        title_font = load_text_card_font(54)
        body_font = load_text_card_font(72)

        card_type = str(card.get("type", "card")).upper()
        body_text = str(card.get("text", "")).strip() or "..."
        wrapped_lines = wrap_text_for_card(draw, body_text, body_font, width - 180)

        draw.rounded_rectangle((90, 110, width - 90, height - 110), radius=36, outline=accent_color, width=6)
        draw.text((130, 160), card_type, font=title_font, fill=title_color)

        line_height = int(body_font.size * 1.4)
        total_height = len(wrapped_lines) * line_height
        y = max(300, (height - total_height) // 2)

        for line in wrapped_lines:
            bbox = draw.textbbox((0, 0), line, font=body_font)
            line_width = bbox[2] - bbox[0]
            x = (width - line_width) // 2
            draw.text((x, y), line, font=body_font, fill=text_color)
            y += line_height

        card_path = FLAT_IMAGE_DIR / f"card_{index}.png"
        image.save(card_path)
        print(f"[OK] TEXT 模式卡图已生成：{card_path}")


def main():
    print("\n==============================")
    print("=== 网页视频生成流程开始 ===")
    print("==============================\n")

    ensure_pipeline_directories()
    log_pipeline_paths()

    input_data = load_url_input()

    if input_data["type"] == "url":
        url = input_data["content"]

        # ⭐ 生成唯一 capture_path
        capture_path = generate_capture_path(url)
        write_capture_path(capture_path)

        # Step 1
        run_step("Step 1：抓取网页截图", ["python", "web_capture.py", url], pipeline_label="web_capture")

        # Step 2
        run_step("Step 2：生成网页解读脚本", ["python", "web_to_script.py"], pipeline_label="web_to_script")
        assert_nonempty_file(SCRIPT_FILE, "script.json")
    elif input_data["type"] == "text":
        text = input_data["content"]

        print("\nStep 2：根据文本生成 script.json")
        script_data = generate_script_from_text(text)
        print(f"[OUTPUT] TEXT 模式卡片数量：{len(script_data.get('cards', []))}")
        assert_nonempty_file(SCRIPT_FILE, "script.json")
    else:
        raise ValueError(f"[ERROR] 不支持的输入类型：{input_data['type']}")

    # Step 3
    run_step("Step 3：生成 scene_plan", ["python", "scene_planner.py"], pipeline_label="scene_planner")
    assert_nonempty_file(SCENE_PLAN_FILE, "scene_plan.json")

    # 🔧 TASK 5B：接入 build_scene_assets
    # 🔧 TASK 5C-A：强制重建 scene_assets，确保与当前 scene_plan 同步
    print("\nStep 3.5：生成 scene_assets 结构适配文件")
    print(f"[PIPELINE] 开始执行 build_scene_assets")
    try:
        # 【新增 TASK 5C-A】删除旧的 scene_assets.json，强制基于当前 scene_plan 重新生成
        if SCENE_ASSETS_FILE.exists():
            try:
                print(f"[PIPELINE] 删除旧 scene_assets：{SCENE_ASSETS_FILE}")
                SCENE_ASSETS_FILE.unlink()
                print(f"[CLEAN] 已删除旧的 scene_assets.json，准备基于当前 scene_plan 重新生成")
            except Exception as e:
                print(f"[ERROR] 删除旧的 scene_assets.json 失败：{str(e)}")
                raise RuntimeError(f"无法清理旧的 scene_assets.json，中断流程")
        
        from build_scene_assets import build_scene_assets
        build_scene_assets()
        
        # 检查生成结果
        assert_nonempty_file(SCENE_ASSETS_FILE, "scene_assets.json")
        print(f"[OK] scene_assets.json 已生成：{SCENE_ASSETS_FILE}")
        
    except Exception as e:
        print(f"[ERROR] build_scene_assets 执行失败：{str(e)}")
        raise RuntimeError(f"无法生成 scene_assets.json，中断流程")

    # Step 4
    if input_data["type"] == "url":
        run_step("Step 4：生成网页卡图", ["python", "web_capture_to_cards_v2.py"], pipeline_label="web_capture_to_cards_v2")
    else:
        print("\nStep 4：生成文本卡图")
        generate_text_cards(script_data.get("cards", []))

    # Step 5
    run_step("Step 5：生成语音", ["python", "tts_engine_main.py"], pipeline_label="tts_engine_main")

    # Step 6
    print(f"[PIPELINE] 开始执行 video_engine / video_builder")
    run_step("Step 6：合成视频", ["python", "-m", "modules.video_engine"], pipeline_label="modules.video_engine")
    assert_nonempty_file(OUTPUT_VIDEO_FILE, "video.mp4")
    print(f"[PIPELINE] 最终输出视频：{OUTPUT_VIDEO_FILE}")
    print("\n==============================")
    print("=== 全流程完成 ===")
    print(f"[OUTPUT] 输出文件：{OUTPUT_VIDEO_FILE}")
    print("==============================\n")


if __name__ == "__main__":
    main()