# -*- coding: utf-8 -*-
"""
tests/test_scene_count_quick.py

快速测试 scene_count 功能的核心逻辑
不运行完整的TTS和视频生成，只验证scene_plan的生成
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules import project_paths

def read_scene_planning():
    """读取生成的 scene_plan.json，返回 scene 数量"""
    scene_plan_file = project_paths.get_data_current_dir() / "scene_plan.json"
    
    if not scene_plan_file.exists():
        return 0
    
    try:
        with open(scene_plan_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if isinstance(data, list):
            return len(data)
        elif isinstance(data, dict) and "scenes" in data:
            return len(data.get("scenes", []))
        
        return 0
    except Exception as e:
        print(f"[ERROR] 读取 scene_plan.json 失败：{e}")
        return 0


def test_scene_planner_direct():
    """直接测试 scene_planner.py 的逻辑"""
    import subprocess
    
    # 先运行一次 scene_planner
    print("运行 scene_planner.py 测试...")
    result = subprocess.run(
        [sys.executable, "scene_planner.py"],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding='utf-8'
    )
    
    if result.returncode != 0:
        print(f"[ERROR] scene_planner 失败：{result.stderr[:200]}")
        return False
    
    print(result.stdout)
    
    # 检查生成的scene数量
    scene_count = read_scene_planning()
    print(f"\n[RESULT] 生成的 scene 数量：{scene_count}")
    
    return scene_count > 0


if __name__ == "__main__":
    # 先运行一次input处理和script生成
    import run_pipeline_web as pipeline_web
    
    print("准备测试数据...")
    input_data = {
        "type": "text",
        "content": "这是一个测试文本。\n用来验证scene_count的控制能力。\n系统应该按照指定的scene数量生成。"
    }
    
    # 生成script
    script_data = pipeline_web.generate_script_from_text(input_data["content"])
    print(f"生成的 script.json，卡片数：{len(script_data.get('cards', []))}")
    
    # 现在测试scene_planner
    success = test_scene_planner_direct()
    
    if success:
        print("\n[OK] scene_planner 正常工作")
    else:
        print("\n[ERROR] scene_planner 失败")
        sys.exit(1)
