#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TASK20-A 工程收敛修复验证脚本
"""

import modules.template_presets as tp
import modules.config as cfg

# 测试 1：validate_template_role 存在
print("✓ TEST 1: validate_template_role 函数存在")
result = tp.validate_template_role("explainer_basic", "hook", warn=False)
print(f"  - validate_template_role('explainer_basic', 'hook') = {result}")
assert result == True, "Should return True for valid role"

# 测试 2：invalid role warning
print("\n✓ TEST 2: invalid role 打印 warning")
result = tp.validate_template_role("explainer_basic", "invalid_role", warn=True)
print(f"  - validate_template_role('explainer_basic', 'invalid_role') = {result}")
assert result == False, "Should return False for invalid role"

# 测试 3：TemplateConfig 存在
print("\n✓ TEST 3: TemplateConfig 存在")
template_config = cfg.TemplateConfig(template_enabled=True, template_name="explainer_basic")
print(f"  - TemplateConfig(template_enabled=True, template_name='explainer_basic')")
print(f"    template_enabled={template_config.template_enabled}")
print(f"    template_name={template_config.template_name}")

# 测试 4：RuntimeConfig 使用 template 字段
print("\n✓ TEST 4: RuntimeConfig 使用 template 字段")
runtime_config = cfg.build_runtime_config(style_name="default", template_name="explainer_basic", template_enabled=True)
print(f"  - runtime_config.template.template_enabled = {runtime_config.template.template_enabled}")
print(f"  - runtime_config.template.template_name = {runtime_config.template.template_name}")
assert runtime_config.template.template_enabled == True
assert runtime_config.template.template_name == "explainer_basic"

# 测试 5：template_enabled=False 时禁用模板
print("\n✓ TEST 5: template_enabled=False 时禁用")
runtime_config_disabled = cfg.build_runtime_config(style_name="default", template_name="explainer_basic", template_enabled=False)
print(f"  - runtime_config.template.template_enabled = {runtime_config_disabled.template.template_enabled}")
print(f"  - runtime_config.template.template_name = {runtime_config_disabled.template.template_name}")
assert runtime_config_disabled.template.template_enabled == False
assert runtime_config_disabled.template.template_name == None  # 禁用时不应设置 template_name

print("\n" + "="*60)
print("✓✓✓ ALL TESTS PASSED - TASK20-A 工程收敛修复完成 ✓✓✓")
print("="*60)
