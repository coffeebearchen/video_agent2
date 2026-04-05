# -*- coding: utf-8 -*-
"""
modules/video_engine.py

功能：
1. 优先读取 scene_assets.json
2. 按 scene_assets 中已绑定的素材生成视频
3. image -> ImageClip
4. video -> VideoFileClip（静音，裁剪到 scene.duration）
5. text_card / 缺失素材 -> 回退到 images/flat/card_x.png，再不行用纯色底图
6. 音频优先读取 script.json 中每个 card 的 audio_file
7. 如果 script.json 没写 audio_file，则尝试 audio/card_x.mp3
8. 输出统一视频文件路径

运行方式：
    cd E:\video_agent
    python -m modules.video_engine
"""

from __future__ import annotations

import json
import math
import os
import shutil
from typing import Any, Dict, List, Optional

from PIL import Image
from moviepy.editor import (
    AudioFileClip,
    ColorClip,
    ImageClip,
    VideoFileClip,
    concatenate_videoclips,
)

from modules import project_paths
from modules.main_chain_bridge_loader import (
    build_bridge_lookup,
    get_bridge_assets_for_scene,
    load_main_chain_bridge,
)
from modules.scene_decision_patch_applier import (
    apply_patch_plan_to_scene_assets,
    load_patch_plan,
)
from modules.scene_decision_debugger import (
    build_scene_decision_record,
    save_scene_decision_debug,
)
from modules.user_scene_asset_loader import load_user_scene_asset_overrides


# =========================
# 路径
# =========================

PROJECT_ROOT = str(project_paths.get_project_root())
DATA_CURRENT_DIR = str(
    getattr(
        project_paths,
        "DATA_CURRENT_DIR",
        project_paths.get_data_current_dir(),
    )
)
SCRIPT_FILE = str(
    getattr(
        project_paths,
        "SCRIPT_JSON_PATH",
        project_paths.get_project_root() / "script.json",
    )
)
SCENE_ASSETS_FILE = str(
    getattr(
        project_paths,
        "SCENE_ASSETS_JSON_PATH",
        project_paths.get_data_current_dir() / "scene_assets.json",
    )
)
IMAGES_DIR = str(
    getattr(
        project_paths,
        "IMAGE_DIR",
        project_paths.get_project_root() / "images" / "flat",
    )
)
AUDIO_DIR = str(
    getattr(
        project_paths,
        "AUDIO_DIR",
        project_paths.get_project_root() / "audio",
    )
)
OUTPUT_DIR = str(
    getattr(
        project_paths,
        "OUTPUT_DIR",
        project_paths.get_project_root() / "output",
    )
)
NORMALIZED_DIR = str(
    getattr(
        project_paths,
        "NORMALIZED_IMAGES_DIR",
        (getattr(project_paths, "OUTPUT_DIR", project_paths.get_project_root() / "output") / "normalized_images"),
    )
)
VIDEO_FILE = str(
    getattr(
        project_paths,
        "OUTPUT_VIDEO",
        (getattr(project_paths, "OUTPUT_DIR", project_paths.get_project_root() / "output") / "video.mp4"),
    )
)
TEMP_AUDIO_FILE = str(
    getattr(
        project_paths,
        "TEMP_AUDIO_FILE",
        (getattr(project_paths, "OUTPUT_DIR", project_paths.get_project_root() / "output") / "temp-audio.m4a"),
    )
)

TARGET_W = 1080
TARGET_H = 1350
FPS = 24
ENABLE_PATCH_APPLY = False
DEFAULT_CARD_DURATION = 4.0
MAIN_CHAIN_BRIDGE_LOOKUP: Dict[Any, Dict[str, Any]] = {}
USER_SCENE_ASSET_LOOKUP: Dict[int, Dict[str, str]] = {}
SCENE_DECISION_RECORDS: List[Dict[str, Any]] = []


# =========================
# 基础工具
# =========================

def ensure_dirs() -> None:
    print(f"[VIDEO] 确保输出目录存在：{OUTPUT_DIR}")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(NORMALIZED_DIR, exist_ok=True)


def load_json_file(path: str) -> Any:
    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到文件：{path}")
    print(f"[VIDEO] 读取 JSON：{path}")
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


def safe_rel(path: Optional[str]) -> str:
    if not path:
        return "(空)"
    try:
        return os.path.relpath(path, PROJECT_ROOT)
    except Exception:
        return path


def resolve_project_path(path_str: Optional[str]) -> Optional[str]:
    """
    把相对路径转为项目根目录下的绝对路径。
    如果本来就是绝对路径，则直接返回。
    """
    if not path_str:
        return None

    path_str = str(path_str).strip()
    if not path_str:
        return None

    if os.path.isabs(path_str):
        return path_str

    return os.path.join(PROJECT_ROOT, path_str)


def remove_old_output() -> None:
    print(f"[VIDEO] 清理旧输出：{VIDEO_FILE}")
    if os.path.exists(VIDEO_FILE):
        try:
            os.remove(VIDEO_FILE)
        except Exception:
            pass

    if os.path.exists(TEMP_AUDIO_FILE):
        try:
            os.remove(TEMP_AUDIO_FILE)
        except Exception:
            pass

    if os.path.exists(NORMALIZED_DIR):
        shutil.rmtree(NORMALIZED_DIR, ignore_errors=True)
    os.makedirs(NORMALIZED_DIR, exist_ok=True)


# =========================
# 数据读取
# =========================

def load_script_cards() -> List[Dict[str, Any]]:
    if not os.path.exists(SCRIPT_FILE):
        print(f"[VIDEO][WARN] 未找到 script.json：{SCRIPT_FILE}")
        print("[VIDEO][WARN] 音频将仅尝试 audio/card_x.mp3 回退方式。")
        return []

    data = load_json_file(SCRIPT_FILE)
    cards = data.get("cards", [])
    if not isinstance(cards, list):
        raise ValueError("script.json 格式错误：cards 必须是 list。")
    return cards


def load_scene_assets() -> List[Dict[str, Any]]:
    """
    兼容两种格式：
    1. 顶层是 list
    2. 顶层是 {"scene_assets": [...]} 
    """
    if not os.path.exists(SCENE_ASSETS_FILE):
        raise FileNotFoundError(f"scene_assets.json 不存在：{SCENE_ASSETS_FILE}")

    data = load_json_file(SCENE_ASSETS_FILE)

    if isinstance(data, list):
        scenes = data
    elif isinstance(data, dict) and "scene_assets" in data and isinstance(data["scene_assets"], list):
        scenes = data["scene_assets"]
    else:
        raise ValueError("scene_assets.json 格式错误，应为 list 或 {'scene_assets': [...]}。")

    return scenes


def load_main_chain_bridge_lookup() -> Dict[Any, Dict[str, Any]]:
    """
    只读加载 bridge 索引。
    bridge 缺失或异常时返回空索引，确保旧主链继续运行。
    """
    bridge_data = load_main_chain_bridge()
    bridge_lookup = build_bridge_lookup(bridge_data)

    if bridge_lookup:
        print(f"[VIDEO] 检测到 bridge，可用 scene 数：{len(bridge_lookup)}")
    else:
        print("[VIDEO] 未使用 bridge，继续旧逻辑")

    return bridge_lookup


def load_safe_patch_plan() -> Optional[Dict[str, Any]]:
    """只读加载 patch 草案；缺失或异常时返回 None。"""
    try:
        patch_plan = load_patch_plan()
    except Exception as error:
        print(f"[VIDEO][WARN] 读取 safe patch plan 失败：{error}")
        return None

    if patch_plan:
        patch_items = patch_plan.get("patch_items", [])
        if isinstance(patch_items, list):
            print(f"[VIDEO][PATCH] 检测到 patch 草案数量：{len(patch_items)}")
    return patch_plan


def apply_safe_patch_hook(scene_assets: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """受控应用 patch 到 scene_assets 内存副本，默认关闭。"""
    if not ENABLE_PATCH_APPLY:
        print("[VIDEO][PATCH] patch 接入默认关闭，继续使用原 scene_assets")
        return scene_assets

    patch_plan = load_safe_patch_plan()
    if not patch_plan:
        print("[VIDEO][PATCH] 未发现可用 patch 草案，继续使用原 scene_assets")
        return scene_assets

    try:
        patched_scene_assets = apply_patch_plan_to_scene_assets(scene_assets, patch_plan)
        print("[VIDEO][PATCH] 已在内存中应用 patch 草案，不写回磁盘")
        return patched_scene_assets
    except Exception as error:
        print(f"[VIDEO][WARN] 内存 patch 应用失败，回退原 scene_assets：{error}")
        return scene_assets


def guess_asset_type_from_path(path_str: Optional[str]) -> Optional[str]:
    """
    根据素材路径后缀推断旧主链可识别的 asset_type。
    仅返回 image / video / None。
    """
    if not path_str:
        return None

    suffix = os.path.splitext(str(path_str).lower())[1]
    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        return "image"
    if suffix in {".mp4", ".mov", ".mkv", ".webm"}:
        return "video"
    return None


def get_bridge_asset_override(
    scene: Dict[str, Any],
    scene_index_zero_based: int,
) -> Optional[Dict[str, str]]:
    """
    尝试从 bridge 中读取当前 scene 的素材覆盖信息。
    优先 primary，其次 secondary。
    仅当路径存在且可推断为 image/video 时才返回覆盖结果。
    否则返回 None，交由旧逻辑继续执行。
    """
    scene_id = scene.get("scene_id", scene_index_zero_based)
    bridge_assets = get_bridge_assets_for_scene(MAIN_CHAIN_BRIDGE_LOOKUP, scene_id)
    if not isinstance(bridge_assets, dict):
        return None

    candidate_paths = [
        bridge_assets.get("primary_asset_path"),
        bridge_assets.get("secondary_asset_path"),
    ]

    for candidate_path in candidate_paths:
        resolved_path = resolve_project_path(candidate_path)
        asset_type = guess_asset_type_from_path(resolved_path)

        if resolved_path and asset_type and os.path.exists(resolved_path):
            print(f"[VIDEO][BRIDGE] scene {scene_id} 使用 bridge 素材：{safe_rel(resolved_path)}")
            decision_source = "bridge_primary"
            reason = "bridge 命中 primary 且文件存在"
            if candidate_path == bridge_assets.get("secondary_asset_path"):
                decision_source = "bridge_secondary"
                reason = "bridge primary 不可用，改用 secondary"
            return {
                "asset_file": resolved_path,
                "asset_type": asset_type,
                "decision_source": decision_source,
                "reason": reason,
            }

    return None


def get_user_asset_override(
    scene: Dict[str, Any],
    scene_index_zero_based: int,
) -> Optional[Dict[str, str]]:
    """
    尝试从用户素材映射中读取当前 scene 的素材覆盖。
    仅当文件存在且类型有效时返回覆盖结果，否则返回 None。
    """
    scene_id = scene.get("scene_id", scene_index_zero_based)
    
    user_asset = USER_SCENE_ASSET_LOOKUP.get(scene_id)
    if not isinstance(user_asset, dict):
        return None
    
    asset_path = user_asset.get("asset_path")
    asset_type = user_asset.get("asset_type")
    
    if asset_path and asset_type and os.path.exists(asset_path):
        print(f"[VIDEO][USER] scene {scene_id} 使用用户素材：{safe_rel(asset_path)}")
        return {
            "asset_file": asset_path,
            "asset_type": asset_type,
            "decision_source": "user_override",
            "reason": "命中用户素材映射",
        }
    
    return None


def append_scene_decision_record(record: Dict[str, Any]) -> None:
    """安全追加调试记录。"""
    SCENE_DECISION_RECORDS.append(record)


def save_scene_decision_debug_safe() -> None:
    """安全保存调试输出，不允许因为调试失败中断主链。"""
    try:
        output_path = save_scene_decision_debug(SCENE_DECISION_RECORDS)
        print(f"[VIDEO][DEBUG] 已保存素材决策调试：{safe_rel(str(output_path))}")
    except Exception as error:
        print(f"[VIDEO][WARN] 保存 scene_decision_debug.json 失败：{error}")


# =========================
# 图片处理
# =========================

def normalize_image_to_target(src_path: str, out_path: str) -> str:
    """
    把图片统一处理为 1080x1350，避免编码时尺寸问题。
    规则：
    - 等比缩放
    - 居中贴到黑底画布
    """
    img = Image.open(src_path).convert("RGB")
    src_w, src_h = img.size

    scale = min(TARGET_W / src_w, TARGET_H / src_h)
    new_w = max(1, int(src_w * scale))
    new_h = max(1, int(src_h * scale))

    resized = img.resize((new_w, new_h), Image.LANCZOS)

    canvas = Image.new("RGB", (TARGET_W, TARGET_H), (0, 0, 0))
    x = (TARGET_W - new_w) // 2
    y = (TARGET_H - new_h) // 2
    canvas.paste(resized, (x, y))

    canvas.save(out_path, quality=95)
    return out_path


def get_fallback_flat_image(scene_index_zero_based: int) -> Optional[str]:
    """
    优先使用 images/flat/card_x.png 作为 text_card / 缺失素材兜底。
    """
    candidates = [
        os.path.join(IMAGES_DIR, f"card_{scene_index_zero_based}.png"),
        os.path.join(IMAGES_DIR, f"card_{scene_index_zero_based}.jpg"),
        os.path.join(IMAGES_DIR, f"card_{scene_index_zero_based}.jpeg"),
    ]

    for path in candidates:
        if os.path.exists(path):
            return path

    common_candidates = [
        os.path.join(IMAGES_DIR, "card_0.png"),
        os.path.join(IMAGES_DIR, "card_0.jpg"),
        os.path.join(IMAGES_DIR, "cover.png"),
    ]
    for path in common_candidates:
        if os.path.exists(path):
            return path

    return None


def build_color_fallback_clip(duration: float):
    """
    最后兜底：纯黑底图。
    """
    return ColorClip(size=(TARGET_W, TARGET_H), color=(0, 0, 0)).set_duration(duration)


# =========================
# 音频处理
# =========================

def get_audio_path_for_scene(scene_index_zero_based: int, script_cards: List[Dict[str, Any]]) -> Optional[str]:
    """
    音频优先级：
    1. script.json cards[i].audio_file
    2. audio/card_i.mp3
    """
    if scene_index_zero_based < len(script_cards):
        audio_file = script_cards[scene_index_zero_based].get("audio_file")
        resolved = resolve_project_path(audio_file)
        if resolved and os.path.exists(resolved):
            return resolved

    fallback_audio = os.path.join(AUDIO_DIR, f"card_{scene_index_zero_based}.mp3")
    if os.path.exists(fallback_audio):
        return fallback_audio

    return None


# =========================
# 场景时长
# =========================

def get_scene_duration(scene: Dict[str, Any], audio_path: Optional[str]) -> float:
    """
    当前规则：
    - 有 scene.duration 就优先用它
    - 但如果音频更长，则取更长值，避免截断语音
    - 都没有就用默认值
    """
    scene_duration = scene.get("duration")
    audio_duration = None

    if audio_path and os.path.exists(audio_path):
        audio_clip = None
        try:
            audio_clip = AudioFileClip(audio_path)
            audio_duration = float(audio_clip.duration)
        finally:
            if audio_clip is not None:
                try:
                    audio_clip.close()
                except Exception:
                    pass

    if scene_duration is None and audio_duration is None:
        return DEFAULT_CARD_DURATION

    if scene_duration is None:
        return max(DEFAULT_CARD_DURATION, float(audio_duration))

    if audio_duration is None:
        return max(DEFAULT_CARD_DURATION, float(scene_duration))

    return max(float(scene_duration), float(audio_duration))


# =========================
# 画面 clip 构建
# =========================

def build_image_clip(image_path: str, duration: float, norm_name: str):
    if not image_path or not os.path.exists(image_path):
        raise FileNotFoundError(f"图片不存在：{image_path}")

    normalized_path = os.path.join(NORMALIZED_DIR, norm_name)
    print(f"[VIDEO] 使用图片：{image_path}")
    normalize_image_to_target(image_path, normalized_path)
    return ImageClip(normalized_path).set_duration(duration)


def build_video_clip(video_path: str, duration: float):
    """
    视频规则：
    - 静音
    - 裁剪到 duration
    - 不足 duration 则循环
    - 统一为 1080x1350（fit + center crop）
    """
    if not video_path or not os.path.exists(video_path):
        raise FileNotFoundError(f"视频不存在：{video_path}")

    print(f"[VIDEO] 使用视频：{video_path}")
    clip = VideoFileClip(video_path).without_audio()

    if clip.duration <= 0:
        raise ValueError(f"视频时长异常：{video_path}")

    if clip.duration < duration:
        loops = int(math.ceil(duration / clip.duration))
        pieces = [VideoFileClip(video_path).without_audio() for _ in range(loops)]
        concat = concatenate_videoclips(pieces, method="compose")
        clip = concat

    clip = clip.subclip(0, duration)

    scale = max(TARGET_W / clip.w, TARGET_H / clip.h)
    new_w = int(clip.w * scale)
    new_h = int(clip.h * scale)

    clip = clip.resize((new_w, new_h))
    x_center = new_w / 2
    y_center = new_h / 2
    clip = clip.crop(
        x_center=x_center,
        y_center=y_center,
        width=TARGET_W,
        height=TARGET_H,
    )

    return clip.set_duration(duration)


def attach_audio_if_exists(clip, audio_path: Optional[str]):
    if not audio_path or not os.path.exists(audio_path):
        print(f"[VIDEO][WARN] 音频不存在：{audio_path}")
        return clip

    print(f"[VIDEO] 使用音频：{audio_path}")
    audio_clip = AudioFileClip(audio_path)
    return clip.set_audio(audio_clip)


def build_scene_visual_clip(
    scene: Dict[str, Any],
    scene_index_zero_based: int,
    script_cards: List[Dict[str, Any]],
):
    """
    为单个 scene 构建最终 clip。
    """
    scene_id = scene.get("scene_id", scene_index_zero_based + 1)
    bridge_item = MAIN_CHAIN_BRIDGE_LOOKUP.get(scene.get("scene_id", scene_index_zero_based))
    bridge_hit = isinstance(bridge_item, dict)
    bridge_status = ""
    bridge_primary_path = ""
    bridge_secondary_path = ""
    if bridge_hit:
        bridge_status = str(bridge_item.get("bridge_status", "") or "")
        bridge_primary_path = str(bridge_item.get("primary_asset_path", "") or "")
        bridge_secondary_path = str(bridge_item.get("secondary_asset_path", "") or "")

    asset_type = scene.get("type")
    asset_file = None
    final_selected_path = ""
    final_selected_type = ""
    decision_source = "old_logic"
    fallback_used = False
    status = "missing"
    reason = "未命中 bridge，尝试旧逻辑"

    # === 第一层：用户素材优先 ===
    user_override = get_user_asset_override(scene, scene_index_zero_based)
    if isinstance(user_override, dict):
        asset_file = user_override.get("asset_file")
        asset_type = user_override.get("asset_type", asset_type)
        decision_source = str(user_override.get("decision_source", "user_override") or "user_override")
        reason = str(user_override.get("reason", "命中用户素材映射") or "命中用户素材映射")

    # === 第二层：bridge ===
    if not asset_file:
        bridge_override = get_bridge_asset_override(scene, scene_index_zero_based)
        if isinstance(bridge_override, dict):
            asset_file = bridge_override.get("asset_file")
            asset_type = bridge_override.get("asset_type", asset_type)
            decision_source = str(bridge_override.get("decision_source", "bridge_primary") or "bridge_primary")
            reason = str(bridge_override.get("reason", "bridge 命中素材") or "bridge 命中素材")

    # === 第三层：旧逻辑 ===

    old_logic_path = resolve_project_path(scene.get("file")) or ""
    old_logic_type = guess_asset_type_from_path(old_logic_path) or str(scene.get("type", "") or "")
    if not asset_file:
        asset_file = old_logic_path or None
        guessed_asset_type = guess_asset_type_from_path(asset_file)
        if asset_type not in {"image", "video"} and guessed_asset_type:
            asset_type = guessed_asset_type
        if asset_file and os.path.exists(asset_file):
            decision_source = "old_logic"
            reason = "bridge 未命中或不可用，回退旧逻辑"
    audio_path = get_audio_path_for_scene(scene_index_zero_based, script_cards)
    duration = get_scene_duration(scene, audio_path)
    fallback_image = get_fallback_flat_image(scene_index_zero_based)

    print("\n" + "=" * 60)
    print(f"scene_id   : {scene_id}")
    print(f"section    : {scene.get('section', '')}")
    print(f"asset_id   : {scene.get('asset_id', '')}")
    print(f"asset_type : {asset_type}")
    print(f"asset_file : {safe_rel(asset_file)}")
    print(f"audio_file : {safe_rel(audio_path)}")
    print(f"duration   : {round(duration, 2)}")

    if asset_type == "image" and asset_file and os.path.exists(asset_file):
        final_selected_path = asset_file
        final_selected_type = "image"
        status = "ready"
        append_scene_decision_record(
            build_scene_decision_record(
                scene_id=scene_id,
                scene_index=scene_index_zero_based,
                bridge_hit=bridge_hit,
                bridge_status=bridge_status,
                bridge_primary_path=bridge_primary_path,
                bridge_secondary_path=bridge_secondary_path,
                old_logic_path=old_logic_path,
                old_logic_type=old_logic_type,
                fallback_path=fallback_image or "",
                final_selected_path=final_selected_path,
                final_selected_type=final_selected_type,
                decision_source=decision_source,
                fallback_used=fallback_used,
                status=status,
                reason=reason,
            )
        )
        clip = build_image_clip(
            image_path=asset_file,
            duration=duration,
            norm_name=f"scene_{scene_index_zero_based:03d}.jpg",
        )
        clip = attach_audio_if_exists(clip, audio_path)
        return clip

    if asset_type == "video" and asset_file and os.path.exists(asset_file):
        final_selected_path = asset_file
        final_selected_type = "video"
        status = "ready"
        append_scene_decision_record(
            build_scene_decision_record(
                scene_id=scene_id,
                scene_index=scene_index_zero_based,
                bridge_hit=bridge_hit,
                bridge_status=bridge_status,
                bridge_primary_path=bridge_primary_path,
                bridge_secondary_path=bridge_secondary_path,
                old_logic_path=old_logic_path,
                old_logic_type=old_logic_type,
                fallback_path=fallback_image or "",
                final_selected_path=final_selected_path,
                final_selected_type=final_selected_type,
                decision_source=decision_source,
                fallback_used=fallback_used,
                status=status,
                reason=reason,
            )
        )
        clip = build_video_clip(
            video_path=asset_file,
            duration=duration,
        )
        clip = attach_audio_if_exists(clip, audio_path)
        return clip

    if fallback_image and os.path.exists(fallback_image):
        print(f"fallback   : 使用 flat 图卡 {safe_rel(fallback_image)}")
        final_selected_path = fallback_image
        final_selected_type = "image"
        decision_source = "fallback_image"
        fallback_used = True
        status = "fallback"
        if bridge_hit or old_logic_path:
            reason = "bridge 与旧逻辑都不可用，改用 flat 图卡"
        else:
            reason = "未找到可用素材，改用 flat 图卡"
        append_scene_decision_record(
            build_scene_decision_record(
                scene_id=scene_id,
                scene_index=scene_index_zero_based,
                bridge_hit=bridge_hit,
                bridge_status=bridge_status,
                bridge_primary_path=bridge_primary_path,
                bridge_secondary_path=bridge_secondary_path,
                old_logic_path=old_logic_path,
                old_logic_type=old_logic_type,
                fallback_path=fallback_image or "",
                final_selected_path=final_selected_path,
                final_selected_type=final_selected_type,
                decision_source=decision_source,
                fallback_used=fallback_used,
                status=status,
                reason=reason,
            )
        )
        clip = build_image_clip(
            image_path=fallback_image,
            duration=duration,
            norm_name=f"fallback_scene_{scene_index_zero_based:03d}.jpg",
        )
        clip = attach_audio_if_exists(clip, audio_path)
        return clip

    print("fallback   : 使用纯色底图")
    decision_source = "fallback_color"
    fallback_used = True
    status = "fallback"
    reason = "所有素材缺失，改用纯色底图"
    append_scene_decision_record(
        build_scene_decision_record(
            scene_id=scene_id,
            scene_index=scene_index_zero_based,
            bridge_hit=bridge_hit,
            bridge_status=bridge_status,
            bridge_primary_path=bridge_primary_path,
            bridge_secondary_path=bridge_secondary_path,
            old_logic_path=old_logic_path,
            old_logic_type=old_logic_type,
            fallback_path=fallback_image or "",
            final_selected_path="",
            final_selected_type="color",
            decision_source=decision_source,
            fallback_used=fallback_used,
            status=status,
            reason=reason,
        )
    )
    clip = build_color_fallback_clip(duration)
    clip = attach_audio_if_exists(clip, audio_path)
    return clip


# =========================
# 资源释放
# =========================

def close_clips(clips: List[Any], final_clip=None) -> None:
    for clip in clips:
        try:
            if getattr(clip, "audio", None):
                clip.audio.close()
        except Exception:
            pass

        try:
            clip.close()
        except Exception:
            pass

    if final_clip is not None:
        try:
            if getattr(final_clip, "audio", None):
                final_clip.audio.close()
        except Exception:
            pass

        try:
            final_clip.close()
        except Exception:
            pass


# =========================
# 主流程
# =========================

def main() -> None:
    global MAIN_CHAIN_BRIDGE_LOOKUP, SCENE_DECISION_RECORDS, USER_SCENE_ASSET_LOOKUP

    if not VIDEO_FILE:
        print("[VIDEO][ERROR] 输出路径未定义")
        return

    ensure_dirs()
    remove_old_output()

    print("[VIDEO] 开始渲染")
    print(f"[VIDEO] scene_assets：{safe_rel(SCENE_ASSETS_FILE)}")
    print(f"[VIDEO] 输出视频：{VIDEO_FILE}")

    SCENE_DECISION_RECORDS = []
    MAIN_CHAIN_BRIDGE_LOOKUP = load_main_chain_bridge_lookup()
    USER_SCENE_ASSET_LOOKUP = load_user_scene_asset_overrides()
    scene_assets = load_scene_assets()
    scene_assets = apply_safe_patch_hook(scene_assets)
    script_cards = load_script_cards()

    if not isinstance(scene_assets, list) or not scene_assets:
        raise ValueError("scene_assets.json 为空，无法生成视频。")

    clips: List[Any] = []
    final_clip = None

    try:
        for idx, scene in enumerate(scene_assets):
            clip = build_scene_visual_clip(
                scene=scene,
                scene_index_zero_based=idx,
                script_cards=script_cards,
            )
            clips.append(clip)

        print("\n[VIDEO] 开始拼接视频")
        print(f"[VIDEO] 输出路径：{VIDEO_FILE}")

        final_clip = concatenate_videoclips(clips, method="compose")

        final_clip.write_videofile(
            VIDEO_FILE,
            fps=FPS,
            codec="libx264",
            audio_codec="aac",
            temp_audiofile=TEMP_AUDIO_FILE,
            remove_temp=True,
            ffmpeg_params=[
                "-pix_fmt",
                "yuv420p",
                "-movflags",
                "+faststart",
            ],
        )

        if not os.path.exists(VIDEO_FILE):
            raise FileNotFoundError(f"视频文件未生成：{VIDEO_FILE}")

        file_size = os.path.getsize(VIDEO_FILE)
        if file_size <= 0:
            raise ValueError(f"视频文件为空：{VIDEO_FILE}")

        print("\n[VIDEO] 渲染完成")
        print(f"[VIDEO] 已生成视频：{safe_rel(VIDEO_FILE)}")
        print(f"[VIDEO] 文件大小：{file_size} bytes")

    finally:
        save_scene_decision_debug_safe()
        close_clips(clips, final_clip)


if __name__ == "__main__":
    main()