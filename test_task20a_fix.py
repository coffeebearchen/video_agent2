#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TASK20-A Fix 验证脚本
"""

import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from modules.config import build_runtime_config

# 测试 1：验证 build_runtime_config 接受命名参数
print("✓ TEST 1: build_runtime_config 接收命名参数")
runtime_config = build_runtime_config(
    style_name=None,
    template_name="test_template",
    template_enabled=True,
)
print(f"  - style_name=None, template_name='test_template', template_enabled=True")
print(f"  - runtime_config.template.template_name = {runtime_config.template.template_name}")
assert runtime_config.template.template_name == "test_template", "template_name 应为 'test_template'"

# 测试 2：验证 template_enabled=False 时禁用
print("\n✓ TEST 2: template_enabled=False 时禁用")
runtime_config_disabled = build_runtime_config(
    style_name=None,
    template_name="test_template",
    template_enabled=False,
)
print(f"  - style_name=None, template_name='test_template', template_enabled=False")
print(f"  - runtime_config.template.template_name = {runtime_config_disabled.template.template_name}")
assert runtime_config_disabled.template.template_name is None, "template_name 应为 None"
assert runtime_config_disabled.template.template_enabled == False, "template_enabled 应为 False"

# 测试 3：验证 template 字段访问
print("\n✓ TEST 3: template 字段访问")
runtime_config = build_runtime_config(
    style_name=None,
    template_name="my_template",
    template_enabled=True,
)
print(f"  - runtime_config.template 存在：{runtime_config.template}")
print(f"  - runtime_config.template.template_name = {runtime_config.template.template_name}")
print(f"  - runtime_config.template.template_enabled = {runtime_config.template.template_enabled}")
assert hasattr(runtime_config, "template"), "runtime_config 应有 template 字段"
assert hasattr(runtime_config.template, "template_name"), "template 应有 template_name 字段"
assert hasattr(runtime_config.template, "template_enabled"), "template 应有 template_enabled 字段"

# 测试 4：验证 None 模板处理
print("\n✓ TEST 4: None 模板处理")
runtime_config_none = build_runtime_config(
    style_name=None,
    template_name=None,
    template_enabled=True,
)
print(f"  - style_name=None, template_name=None, template_enabled=True")
print(f"  - runtime_config.template.template_name = {runtime_config_none.template.template_name}")
assert runtime_config_none.template.template_name is None, "template_name 应为 None"

print("\n" + "="*60)
print("✓✓✓ ALL TESTS PASSED - TASK20-A Fix 验证完成 ✓✓✓")
print("="*60)
