from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from PIL import Image

from modules.content_input_adapter import build_content_input_from_pipeline
from modules.content_spec import build_default_content_spec
from modules.overlay_renderer import build_text_overlay_image
from modules.overlay_style_engine import (
    build_highlight_display_text,
    emit_text_spec_debug,
    get_highlight_spec,
    get_runtime_style_name,
    get_title_spec,
)
from modules.text_spec import build_default_text_spec


PROJECT_ROOT = Path(__file__).resolve().parent.parent
FONTS_DIR = PROJECT_ROOT / "fonts"
DEFAULT_OUTPUT_PATH = PROJECT_ROOT / "output" / "preview.png"


def _paste_centered(base_image: Image.Image, overlay_path: str | None, position_y: int) -> None:
    if not overlay_path:
        return

    overlay_image = Image.open(overlay_path).convert("RGBA")
    paste_x = max(0, (base_image.width - overlay_image.width) // 2)
    paste_y = max(0, position_y)
    base_image.paste(overlay_image, (paste_x, paste_y), overlay_image)


def generate_preview_frame(
    style_name: str,
    output_path: str = "output/preview.png",
    input_data: Dict[str, Any] | None = None,
    pipeline_input: Dict[str, Any] | None = None,
) -> Path:
    """Preview-A：生成单帧预览（不依赖 video）。"""
    resolved_style_name = get_runtime_style_name(style_name)
    output_file = Path(output_path)
    if not output_file.is_absolute():
        output_file = PROJECT_ROOT / output_file
    output_file.parent.mkdir(parents=True, exist_ok=True)

    print(f"[PREVIEW] start style={resolved_style_name}")

    width, height = 720, 1280
    image = Image.new("RGBA", (width, height), (0, 0, 0, 255))

    if input_data is None:
        content_input = build_content_input_from_pipeline(pipeline_input)
    else:
        content_input = dict(input_data)

    content_spec = build_default_content_spec(content_input)
    text_spec = build_default_text_spec(resolved_style_name)
    title_spec = get_title_spec(resolved_style_name)
    highlight_spec = get_highlight_spec(resolved_style_name)
    title = str(content_spec.get("title", {}).get("text", "Default Title") or "Default Title")
    highlight_text = {
        "zh": str(content_spec.get("highlight", {}).get("zh", "默认高亮内容") or "默认高亮内容"),
        "en": str(content_spec.get("highlight", {}).get("en", "Default highlight") or "Default highlight"),
    }
    highlight_text = build_highlight_display_text(
        highlight_text["zh"],
        highlight_text["en"],
        style_name=resolved_style_name,
    )

    print(f"[CONTENT_SPEC] title={title}")
    print(f"[CONTENT_SPEC] title_len={len(title)}")
    print(f"[CONTENT_SPEC] highlight_zh={content_spec['highlight']['zh']}")
    print(f"[CONTENT_SPEC] highlight_zh_len={len(content_spec['highlight']['zh'])}")
    print(f"[CONTENT_SPEC] highlight_en={content_spec['highlight']['en']}")
    print(f"[CONTENT_SPEC] highlight_en_len={len(content_spec['highlight']['en'])}")
    print(f"[PREVIEW] title={title}")
    print(f"[PREVIEW] highlight={content_spec['highlight']['zh']}")
    emit_text_spec_debug(resolved_style_name)

    preview_layers_dir = output_file.parent / "preview_layers"
    preview_layers_dir.mkdir(parents=True, exist_ok=True)

    title_path = build_text_overlay_image(
        str(preview_layers_dir / f"preview_title_{resolved_style_name}.png"),
        title,
        str(FONTS_DIR),
        int(title_spec.get("font_size", 58) or 58),
        min(width - 120, int(title_spec.get("max_width", 920) or 920)),
        tuple(title_spec.get("text_color", (248, 249, 250, 255))),
        tuple(title_spec.get("bg_color", (10, 10, 10, 145))),
        padding_x=int(title_spec.get("padding_x", 28) or 28),
        padding_y=int(title_spec.get("padding_y", 20) or 20),
        radius=int(title_spec.get("radius", 24) or 24),
    )
    _paste_centered(image, title_path, int(title_spec.get("position_y", 96) or 96))

    highlight_path = build_text_overlay_image(
        str(preview_layers_dir / f"preview_highlight_{resolved_style_name}.png"),
        highlight_text,
        str(FONTS_DIR),
        int(highlight_spec.get("font_size", 60) or 60),
        min(width - 180, int(highlight_spec.get("max_width", 760) or 760)),
        tuple(highlight_spec.get("text_color", (255, 179, 71, 255))),
        tuple(highlight_spec.get("bg_color", (25, 25, 25, 190))),
        padding_x=int(highlight_spec.get("padding_x", 28) or 28),
        padding_y=int(highlight_spec.get("padding_y", 20) or 20),
        radius=int(highlight_spec.get("radius", 24) or 24),
    )
    highlight_y = max(220, int(height * float(highlight_spec.get("position_ratio_y", 0.42) or 0.42)))
    _paste_centered(image, highlight_path, highlight_y)

    image.convert("RGB").save(output_file)

    print(f"[PREVIEW] content_spec={content_spec}")
    print(f"[PREVIEW] text_spec={text_spec}")
    print(f"[PREVIEW] saved: {output_file}")
    return output_file