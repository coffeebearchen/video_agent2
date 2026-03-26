# -*- coding: utf-8 -*-
"""
tools/test_asset_selector.py - TASK 6A 通过版本

作用：
独立测试素材选择器
验证关键词匹配规则是否正常工作
"""

import sys
import json
from pathlib import Path

# 将项目根目录加入 sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from asset_selector import select_asset_for_text


def main():
    print("\n" + "=" * 70)
    print("🧪 素材选择器测试")
    print("=" * 70 + "\n")
    
    # 测试数据
    test_cases = [
        {
            "id": 1,
            "text": "这其实是网站为了安全，在检查你的访问是否合法。",
            "expected_keyword": "安全 或 验证",
            "expected_asset": "security.png"
        },
        {
            "id": 2,
            "text": "就像进小区前，保安会看一眼你的门禁卡。",
            "expected_keyword": "保安 或 门禁 或 小区",
            "expected_asset": "gate.png"
        },
        {
            "id": 3,
            "text": "伊朗和以色列互相袭击了对方的天然气设施。",
            "expected_keyword": "伊朗 或 以色列 或 袭击",
            "expected_asset": "conflict.png"
        },
        {
            "id": 4,
            "text": "今天我们打开一个网页，看看这个页面的结构。",
            "expected_keyword": "网页 或 页面",
            "expected_asset": "browser.png"
        },
        {
            "id": 5,
            "text": "这是一个普通说明，没有特定关键词。",
            "expected_keyword": "无",
            "expected_asset": "fallback (text_card)"
        },
    ]
    
    # 运行测试
    passed = 0
    failed = 0
    
    for case in test_cases:
        print(f"测试 #{case['id']}")
        print(f"  输入文本：{case['text']}")
        print(f"  期望关键词：{case['expected_keyword']}")
        print(f"  期望素材：{case['expected_asset']}")
        
        # 调用选择器
        result = select_asset_for_text(case['text'])
        
        print(f"  实际结果：")
        print(f"    - matched: {result['matched']}")
        print(f"    - asset_type: {result['asset_type']}")
        print(f"    - asset_file: {result['asset_file']}")
        print(f"    - keyword: {result['keyword']}")
        print(f"    - reason: {result['reason']}")
        
        # 简单验证（基于 matched 状态）
        if case['id'] == 5:
            # 最后一条应该是 fallback
            if not result['matched'] and result['asset_type'] == 'text_card':
                status = "✅ PASS"
                passed += 1
            else:
                status = "❌ FAIL"
                failed += 1
        else:
            # 其他应该匹配上
            if result['matched'] and result['asset_file'] != "":
                status = "✅ PASS"
                passed += 1
            else:
                status = "❌ FAIL"
                failed += 1
        
        print(f"  状态：{status}\n")
    
    # 统计
    print("=" * 70)
    print(f"📊 测试统计：{passed} 通过，{failed} 失败")
    print("=" * 70 + "\n")
    
    # 额外的示例展示
    print("📝 额外示例：\n")
    
    extra_examples = [
        "用户访问了一个恶意网站。",
        "国家安全部门检查电子产品。",
        "社区门禁系统升级。",
        "中东地区冲突加剧。",
        "天气变冷了。",
    ]
    
    for text in extra_examples:
        result = select_asset_for_text(text)
        print(f"文本：{text}")
        print(f"  → {result['asset_type']}: {result['asset_file']}")
        if result['keyword']:
            print(f"    （关键词命中：'{result['keyword']}'）")
        else:
            print(f"    （无特定关键词命中，使用 fallback）")
        print()


if __name__ == "__main__":
    main()
