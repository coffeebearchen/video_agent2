# -*- coding: utf-8 -*-
"""
run_pipeline_user.py

【用户统一入口层｜最小可用产品入口】

作用：
1. 接收用户输入（text / url）
2. 调用现有输入处理与主链模块
3. 自动完成 script / plan / scene_assets / TTS / video 全流程
4. 输出最终视频路径与文件大小

边界：
- 不修改已有核心模块逻辑
- 不改变默认渲染逻辑
- 不自动开启 patch apply
- 保持 CLI 可直接运行
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

from input_handler import InputHandler
from build_scene_assets import build_scene_assets
import run_pipeline_web as pipeline_web
import scene_planner


PROJECT_ROOT = Path(__file__).resolve().parent
INPUT_JSON_FILE = PROJECT_ROOT / "input.json"
DATA_CURRENT_DIR = PROJECT_ROOT / "data" / "current"
ELEMENT_PLAN_FILE = DATA_CURRENT_DIR / "element_plan.json"
TIMING_PLAN_FILE = DATA_CURRENT_DIR / "timing_plan.json"
OUTPUT_VIDEO_FILE = Path(str(pipeline_web.OUTPUT_VIDEO_FILE))
SCENE_ASSETS_FILE = Path(str(pipeline_web.SCENE_ASSETS_FILE))


def get_user_input() -> Dict[str, Any]:
    """获取并校验用户输入。"""
    handler = InputHandler()

    print("请输入内容类型（text/url）：")
    input_type = input("> ").strip().lower()

    if input_type not in {"text", "url"}:
        raise ValueError("仅支持 text 或 url")

    if input_type == "text":
        print("\n请输入内容：")
        content = input("> ").strip()
        parsed_input = handler.parse_text(content, source="cli")
    else:
        print("\n请输入网页链接：")
        content = input("> ").strip()
        parsed_input = handler.parse_url(content, source="cli")

    INPUT_JSON_FILE.write_text(
        json.dumps(parsed_input, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[INPUT] 已写入标准输入文件：{INPUT_JSON_FILE}")
    return parsed_input


def run_python_step(title: str, args: list[str]) -> None:
    """使用当前 Python 解释器执行既有脚本。"""
    print(f"\n{title}")
    command = [sys.executable, *args]
    result = subprocess.run(command, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        raise RuntimeError(f"执行失败：{' '.join(args)}")


def assert_nonempty_file(path: Path, label: str) -> None:
    """校验关键输出文件存在且非空。"""
    if not path.exists():
        raise RuntimeError(f"{label} 不存在：{path}")
    if path.stat().st_size <= 0:
        raise RuntimeError(f"{label} 文件大小为 0：{path}")


def run_pipeline(input_data: Dict[str, Any], scene_count: int | None = None) -> Path:
    """
    按统一顺序执行现有主链。
    
    Args:
        input_data: 输入数据字典 (type, content)
        scene_count: 可选的场景数量控制 (None=自动, 3=3个scene, 5=5个scene)
    """
    print("\n==============================")
    print("正在生成视频...")
    print("==============================")

    if scene_count is not None:
        print(f"[SCENE_COUNT] mode=fixed | target={scene_count}")
    else:
        print("[SCENE_COUNT] mode=auto")

    pipeline_web.ensure_pipeline_directories()
    pipeline_web.log_pipeline_paths()

    script_data: Dict[str, Any] | None = None

    if input_data["type"] == "url":
        url = str(input_data["content"])
        capture_path = pipeline_web.generate_capture_path(url)
        pipeline_web.write_capture_path(capture_path)

        run_python_step("Step 1：抓取网页截图", ["web_capture.py", url])
        run_python_step("Step 2：生成网页解读脚本", ["web_to_script.py"])
        pipeline_web.assert_nonempty_file(pipeline_web.SCRIPT_FILE, "script.json")
    else:
        text = str(input_data["content"])
        print("\nStep 1：根据文本生成 script.json")
        script_data = pipeline_web.generate_script_from_text(text)
        print(f"[OUTPUT] TEXT 模式卡片数量：{len(script_data.get('cards', []))}")
        pipeline_web.assert_nonempty_file(pipeline_web.SCRIPT_FILE, "script.json")

    print("\nStep 3：生成 scene_plan")
    scene_planner.main(scene_count=scene_count)
    pipeline_web.assert_nonempty_file(pipeline_web.SCENE_PLAN_FILE, "scene_plan.json")

    run_python_step("Step 4：生成 element_plan", ["element_builder.py"])
    assert_nonempty_file(ELEMENT_PLAN_FILE, "element_plan.json")

    run_python_step("Step 5：生成 timing_plan", ["timing_engine.py"])
    assert_nonempty_file(TIMING_PLAN_FILE, "timing_plan.json")

    print("\nStep 6：生成 scene_assets")
    if SCENE_ASSETS_FILE.exists():
        SCENE_ASSETS_FILE.unlink()
        print(f"[CLEAN] 已删除旧 scene_assets：{SCENE_ASSETS_FILE}")
    build_scene_assets()
    assert_nonempty_file(SCENE_ASSETS_FILE, "scene_assets.json")

    if input_data["type"] == "url":
        run_python_step("Step 7：生成网页卡图", ["web_capture_to_cards_v2.py"])
    else:
        print("\nStep 7：生成文本卡图")
        pipeline_web.generate_text_cards((script_data or {}).get("cards", []))

    run_python_step("Step 8：生成语音", ["tts_engine_main.py"])
    run_python_step("Step 9：合成视频", ["-m", "modules.video_engine"])
    assert_nonempty_file(OUTPUT_VIDEO_FILE, "video.mp4")

    return OUTPUT_VIDEO_FILE


def main() -> None:
    """
    CLI 主入口。
    
    可选命令行参数：
        python run_pipeline_user.py [scene_count]
        
    例如：
        python run_pipeline_user.py         # 默认自动模式
        python run_pipeline_user.py 3       # 指定 3 个 scene
        python run_pipeline_user.py 5       # 指定 5 个 scene
    """
    try:
        # 检查命令行参数中是否指定了 scene_count
        scene_count = None
        if len(sys.argv) > 1:
            try:
                scene_count = int(sys.argv[1])
                if scene_count not in (3, 5):
                    print(f"[WARN] scene_count 仅支持 3 或 5，不支持 {scene_count}，将使用自动模式")
                    scene_count = None
            except (ValueError, IndexError):
                print(f"[WARN] scene_count 参数无效，将使用自动模式")
                scene_count = None
        
        input_data = get_user_input()
        video_path = run_pipeline(input_data, scene_count=scene_count)
        video_size = video_path.stat().st_size
    except KeyboardInterrupt:
        print("\n已取消执行。")
        return
    except Exception as error:
        print(f"\n[ERROR] 生成失败：{error}")
        return

    print("\n==============================")
    print("视频生成完成：")
    print(video_path)
    print(f"视频大小：{video_size} bytes")
    print("[OK] 生成成功")
    print("==============================")


if __name__ == "__main__":
    main()