#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件名：test_template_system.py
作用说明：快速测试模板系统的各个功能

运行方式：
    python test_template_system.py
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from modules.template_presets import (
    list_available_templates,
    get_template_preset,
    get_template_default_roles,
    get_template_role_defaults,
    is_valid_template_role,
)
from modules.config import build_runtime_config


def test_list_templates():
    """测试：列出所有可用模板"""
    print("\n" + "="*60)
    print("TEST 1: 列出所有可用模板")
    print("="*60)
    
    templates = list_available_templates()
    print(f"✓ 可用模板列表：{templates}")
    assert len(templates) == 3, "应该有 3 个模板"
    print("✓ 模板数量正确（3 个）")


def test_get_template():
    """测试：获取模板完整定义"""
    print("\n" + "="*60)
    print("TEST 2: 获取模板完整定义")
    print("="*60)
    
    template = get_template_preset("explainer_basic")
    print(f"✓ 获取 explainer_basic 模板")
    
    assert template is not None, "应该获得模板定义"
    assert "display_name" in template, "应该有 display_name"
    assert "default_roles" in template, "应该有 default_roles"
    assert "role_defaults" in template, "应该有 role_defaults"
    
    print(f"  - display_name: {template['display_name']}")
    print(f"  - description: {template['description']}")
    print(f"  - default_roles: {template['default_roles']}")
    print("✓ 模板定义完整")


def test_default_roles():
    """测试：获取模板的默认角色列表"""
    print("\n" + "="*60)
    print("TEST 3: 获取模板的默认角色列表")
    print("="*60)
    
    roles = get_template_default_roles("explainer_basic")
    print(f"✓ explainer_basic 的默认角色：{roles}")
    assert roles == ["hook", "explain", "example", "summary"], "角色列表应该正确"
    print("✓ 角色列表验证通过")
    
    roles = get_template_default_roles("product_pitch")
    print(f"✓ product_pitch 的默认角色：{roles}")
    assert roles == ["pain_point", "solution", "proof", "call_to_action"], "角色列表应该正确"
    print("✓ 角色列表验证通过")


def test_role_defaults():
    """测试：获取角色的默认值"""
    print("\n" + "="*60)
    print("TEST 4: 获取角色的默认值")
    print("="*60)
    
    # 测试 explainer_basic 的 hook 角色
    defaults = get_template_role_defaults("explainer_basic", "hook")
    print(f"✓ explainer_basic.hook 的默认值：")
    print(f"  - segment_animation_enabled: {defaults.get('segment_animation_enabled')}")
    print(f"  - segment_animation: {defaults.get('segment_animation')}")
    print(f"  - highlight_enabled: {defaults.get('highlight_enabled')}")
    print(f"  - default_insert_position: {defaults.get('default_insert_position')}")
    print(f"  - default_insert_scale: {defaults.get('default_insert_scale')}")
    
    assert defaults.get("segment_animation") == "slide_up", "动画类型应该是 slide_up"
    assert defaults.get("default_insert_position") == "top", "位置应该是 top"
    print("✓ 角色默认值验证通过")
    
    # 测试 product_pitch 的 solution 角色
    defaults = get_template_role_defaults("product_pitch", "solution")
    print(f"✓ product_pitch.solution 的默认值：")
    print(f"  - segment_animation: {defaults.get('segment_animation')}")
    print(f"  - emphasis_strength: {defaults.get('emphasis_strength')}")
    assert defaults.get("segment_animation") == "zoom_in", "动画类型应该是 zoom_in"
    print("✓ 角色默认值验证通过")


def test_valid_role():
    """测试：验证角色有效性"""
    print("\n" + "="*60)
    print("TEST 5: 验证角色有效性")
    print("="*60)
    
    # 有效角色
    result = is_valid_template_role("explainer_basic", "hook")
    print(f"✓ is_valid_template_role('explainer_basic', 'hook') = {result}")
    assert result is True, "应该是有效角色"
    
    # 无效角色
    result = is_valid_template_role("explainer_basic", "invalid_role")
    print(f"✓ is_valid_template_role('explainer_basic', 'invalid_role') = {result}")
    assert result is False, "应该是无效角色"
    
    # 无效模板
    result = is_valid_template_role("invalid_template", "hook")
    print(f"✓ is_valid_template_role('invalid_template', 'hook') = {result}")
    assert result is False, "应该是无效模板"
    
    print("✓ 角色验证通过")


def test_runtime_config():
    """测试：RuntimeConfig 集成模板信息"""
    print("\n" + "="*60)
    print("TEST 6: RuntimeConfig 集成模板信息")
    print("="*60)
    
    # 不带模板
    config = build_runtime_config(style_name="default")
    print(f"✓ 不带模板的 RuntimeConfig(style='default')：")
    print(f"  - template_name: {config.template_name}")
    assert config.template_name is None, "没有指定模板应该是 None"
    
    # 带模板
    config = build_runtime_config(style_name="default", template_name="explainer_basic")
    print(f"✓ 带模板的 RuntimeConfig(style='default', template='explainer_basic')：")
    print(f"  - template_name: {config.template_name}")
    assert config.template_name == "explainer_basic", "模板名应该正确"
    
    # 模板名正规化（大写变小写）
    config = build_runtime_config(template_name="EXPLAINER_BASIC")
    print(f"✓ 模板名正规化 RuntimeConfig(template='EXPLAINER_BASIC')：")
    print(f"  - template_name: {config.template_name}")
    assert config.template_name == "explainer_basic", "应该正规化为小写"
    
    print("✓ RuntimeConfig 集成验证通过")


def test_template_fallback_animation():
    """测试：动画 fallback 逻辑（模拟 segment_engine 用法）"""
    print("\n" + "="*60)
    print("TEST 7: 动画 fallback 逻辑（模拟 segment_engine）")
    print("="*60)
    
    from modules.segment_engine import get_template_fallback_animation
    
    config = build_runtime_config(template_name="explainer_basic")
    
    # Scene 1: 有 template_role，应该返回模板默认值
    scene1 = {"id": 1, "template_role": "hook", "text": "Test"}
    result = get_template_fallback_animation(scene1, config)
    print(f"✓ Scene with template_role='hook'：{result}")
    assert result == "slide_up", "应该返回 slide_up"
    
    # Scene 2: 无 template_role，应该返回 None
    scene2 = {"id": 2, "text": "Test (no role)"}
    result = get_template_fallback_animation(scene2, config)
    print(f"✓ Scene without template_role：{result}")
    assert result is None, "无 template_role 应该返回 None"
    
    # Scene 3: 无模板的 config，应该返回 None
    config_no_template = build_runtime_config()
    scene3 = {"id": 3, "template_role": "hook", "text": "Test"}
    result = get_template_fallback_animation(scene3, config_no_template)
    print(f"✓ Config without template：{result}")
    assert result is None, "无模板的 config 应该返回 None"
    
    print("✓ 动画 fallback 验证通过")


def test_template_fallback_insert():
    """测试：插入 fallback 逻辑（模拟 visual_insert_engine 用法）"""
    print("\n" + "="*60)
    print("TEST 8: 插入 fallback 逻辑（模拟 visual_insert_engine）")
    print("="*60)
    
    from modules.visual_insert_engine import (
        get_template_fallback_insert_position,
        get_template_fallback_insert_scale,
    )
    
    config = build_runtime_config(template_name="explainer_basic")
    
    # 位置 fallback
    scene = {"id": 1, "template_role": "explain", "text": "Test"}
    position = get_template_fallback_insert_position(scene, config)
    scale = get_template_fallback_insert_scale(scene, config)
    print(f"✓ Scene with template_role='explain'：")
    print(f"  - position: {position}")
    print(f"  - scale: {scale}")
    assert position == "center", "位置应该是 center"
    assert scale == 0.72, "缩放应该是 0.72"
    
    print("✓ 插入 fallback 验证通过")


def main():
    """运行所有测试"""
    print("\n" + "█"*60)
    print("█" + " "*58 + "█")
    print("█" + " "*10 + "TEMPLATE SYSTEM - QUICK TEST SUITE" + " "*14 + "█")
    print("█" + " "*58 + "█")
    print("█"*60)
    
    try:
        test_list_templates()
        test_get_template()
        test_default_roles()
        test_role_defaults()
        test_valid_role()
        test_runtime_config()
        test_template_fallback_animation()
        test_template_fallback_insert()
        
        print("\n" + "█"*60)
        print("█" + " "*15 + "✓ 所有测试通过！模板系统正常工作" + " "*8 + "█")
        print("█"*60 + "\n")
        
        return 0
    
    except AssertionError as e:
        print(f"\n❌ 测试失败：{e}")
        return 1
    
    except Exception as e:
        print(f"\n❌ 异常错误：{e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
