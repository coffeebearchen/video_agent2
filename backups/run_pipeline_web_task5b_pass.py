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

import subprocess
from datetime import datetime
from pathlib import Path
import re

BASE_DIR = Path(__file__).resolve().parent
CURRENT_CAPTURE_PATH_FILE = BASE_DIR / "current_capture_path.txt"
WEB_CAPTURE_DIR = BASE_DIR / "assets" / "web_capture"
DATA_CURRENT_DIR = BASE_DIR / "data" / "current"
SCENE_ASSETS_FILE = DATA_CURRENT_DIR / "scene_assets.json"


def safe_name(text: str):
    text = re.sub(r"[\\/:*?\"<>|]", "_", text)
    text = re.sub(r"\s+", "_", text)
    return text[:60]


def generate_capture_path(url: str):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe = safe_name(url.replace("https://", "").replace("http://", ""))
    path = WEB_CAPTURE_DIR / f"{timestamp}_{safe}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_capture_path(path: Path):
    CURRENT_CAPTURE_PATH_FILE.write_text(str(path), encoding="utf-8")
    print(f"📌 主链生成 capture_path：{path}")


def run_step(title, cmd):
    print(f"\n{title}")
    result = subprocess.run(cmd, cwd=BASE_DIR)
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
        URL 字符串
    
    异常：
        ValueError: type 不是 url，或格式校验失败
    """
    input_json_path = BASE_DIR / "input.json"
    
    # ===== 尝试读取 input.json =====
    if input_json_path.exists():
        try:
            from input_handler import InputFileHandler
            
            handler = InputFileHandler(str(input_json_path))
            data = handler.read_from_file()
            
            # 检查类型：当前主链仅支持 url
            if data.get('type') != 'url':
                raise ValueError(
                    f"❌ 当前主链尚未接入 {data.get('type')} 模式，"
                    f"请改用 type='url' 或继续使用手动 URL 输入。"
                )
            
            url = data.get('content', '').strip()
            if not url:
                raise ValueError("❌ input.json 中 content 不能为空")
            
            print(f"📥 从 input.json 读取 URL：{url}")
            return url
            
        except ValueError:
            # 校验失败，直接抛出（不自动降级到手动输入）
            raise
        except Exception as e:
            # input.json 存在但格式有问题，明确报错
            raise ValueError(
                f"❌ 读取 input.json 失败：{str(e)}"
            )
    
    # ===== 无 input.json，手动输入 =====
    url = input("请输入网页 URL：").strip()
    if not url:
        raise ValueError("URL 不能为空")
    
    return url


def main():
    print("\n==============================")
    print("🚀 网页视频生成流程开始")
    print("==============================\n")

    url = load_url_input()

    # ⭐ 生成唯一 capture_path
    capture_path = generate_capture_path(url)
    write_capture_path(capture_path)

    # Step 1
    run_step("🌐 Step 1：抓取网页截图", ["python", "web_capture.py", url])

    # Step 2
    run_step("🧠 Step 2：生成网页解读脚本", ["python", "web_to_script.py"])

    # Step 3
    run_step("🧩 Step 3：生成 scene_plan", ["python", "scene_planner.py"])

    # 🔧 TASK 5B：接入 build_scene_assets
    print("\n🧩 Step 3.5：生成 scene_assets 结构适配文件")
    try:
        from build_scene_assets import build_scene_assets
        build_scene_assets()
        
        # 检查生成结果
        if not SCENE_ASSETS_FILE.exists():
            raise RuntimeError(
                f"❌ build_scene_assets 执行后，scene_assets.json 未生成"
            )
        print(f"✅ scene_assets.json 已生成：{SCENE_ASSETS_FILE}")
        
    except Exception as e:
        print(f"❌ build_scene_assets 执行失败：{str(e)}")
        raise RuntimeError(f"无法生成 scene_assets.json，中断流程")

    # Step 4
    run_step("🖼 Step 4：生成网页卡图", ["python", "web_capture_to_cards_v2.py"])

    # Step 5
    run_step("🔊 Step 5：生成语音", ["python", "tts_engine_main.py"])

    # Step 6
    run_step("🎬 Step 6：合成视频", ["python", "-m", "modules.video_engine"])
    print("\n==============================")
    print("✅ 全流程完成！")
    print("📦 输出文件：output/video.mp4")
    print("==============================\n")


if __name__ == "__main__":
    main()
