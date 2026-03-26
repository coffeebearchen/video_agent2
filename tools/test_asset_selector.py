# -*- coding: utf-8 -*-
"""
tools/test_asset_selector.py

作用：
独立测试素材选择器
验证关键词匹配规则是否正常工作（TASK 6C：扩展规则库）
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
    print("🧪 素材选择器测试（TASK 6C 扩展版）")
    print("=" * 70 + "\n")
    
    # 核心测试数据（包含原有的2个 + 新增的4个）
    test_cases = [
        # 原有测试用例（保持兼容性）
        {
            "id": 1,
            "text": "这其实是网站为了安全，在检查你的访问是否合法。",
            "expected_keyword": "安全",
            "expected_asset": "security.png",
            "category": "安全/验证类"
        },
        {
            "id": 2,
            "text": "就像进小区前，保安会看一眼你的门禁卡。",
            "expected_keyword": "保安",
            "expected_asset": "gate.png",
            "category": "门禁/保安类"
        },
        {
            "id": 3,
            "text": "伊朗和以色列互相袭击了对方的天然气设施。",
            "expected_keyword": "袭击",
            "expected_asset": "conflict.png",
            "category": "冲突/战争类"
        },
        {
            "id": 4,
            "text": "今天我们打开一个网页，看看这个页面的结构。",
            "expected_keyword": "网页",
            "expected_asset": "browser.png",
            "category": "网页/浏览器类"
        },
        # TASK 6C 新增测试用例
        {
            "id": 5,
            "text": "很多人每天都在听一个词：国债，但其实并不知道它到底是什么。",
            "expected_keyword": "国债",
            "expected_asset": "finance.png",
            "category": "金融/货币/债券类"
        },
        {
            "id": 6,
            "text": "而像比特币这样的数字资产，则是一种完全不同的价值体系。",
            "expected_keyword": "比特币",
            "expected_asset": "finance.png",
            "category": "金融/货币/债券类"
        },
        {
            "id": 7,
            "text": "福州的魅力，藏在它热闹的市井生活和街头巷尾的烟火气里。",
            "expected_keyword": "街头",
            "expected_asset": "city.png",
            "category": "城市/旅游类（市井生活优先级低于城市）"
        },
        {
            "id": 8,
            "text": "清晨的早市人声鼎沸，老手艺人在坊巷里安静地做着小吃。",
            "expected_keyword": "小吃",
            "expected_asset": "food.png",
            "category": "美食/生活类"
        },
        {
            "id": 9,
            "text": "现在很多平台都在用 AI 模型提升应用体验。",
            "expected_keyword": "AI",
            "expected_asset": "tech.png",
            "category": "科技/AI/软件类"
        },
        {
            "id": 10,
            "text": "这是一个普通说明，没有特定关键词。",
            "expected_keyword": "无",
            "expected_asset": "fallback (text_card)",
            "category": "Fallback"
        },
    ]
    
    # 运行测试
    passed = 0
    failed = 0
    
    for case in test_cases:
        print(f"测试 #{case['id']} [{case['category']}]")
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
        if case['id'] == 10:
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
    print("📝 额外示例（TASK 6C 新增）：\n")
    
    extra_examples = [
        ("用户访问了一个恶意网站。", "browser.png"),
        ("国家安全部门检查电子产品。", "security.png"),
        ("社区门禁系统升级。", "gate.png"),
        ("中东地区冲突加剧。", "conflict.png"),
        ("收益率和利率的区别。", "finance.png"),
        ("人工智能正在改变世界。", "tech.png"),
        ("古城里的文化底蕴。", "city.png"),
        ("早市的烟火气。", "food.png"),
        ("天气变冷了。", "text_card (fallback)"),
    ]
    
    for text, expected in extra_examples:
        result = select_asset_for_text(text)
        actual = result['asset_file'].split('/')[-1] if result['asset_file'] else 'text_card (fallback)'
        status = "✅" if actual == expected else "⚠️"
        print(f"{status} 文本：{text}")
        print(f"    预期：{expected}")
        print(f"    实际：{actual}")
        if result['keyword']:
            print(f"    关键词：'{result['keyword']}'")
        print()


if __name__ == "__main__":
    main()

