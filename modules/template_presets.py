# -*- coding: utf-8 -*-
"""
文件名：template_presets.py
作用说明：
1. 定义所有可用的视频模板与模板角色
2. 为每个模板角色提供默认表达行为（唯一真源）
3. 提供模板读取、查询、校验接口
4. 支持 template_role 非法检测与 warning 提示

本次改动点（TASK20-A）：
1. 新增 validate_template_role() 校验函数
2. 新增 get_validated_template_role() 函数，支持 warning 提示
3. 明确标注：所有模板行为定义都在此文件，禁止下游硬编码
"""


# ===== 模板定义 ===== 
# 模板为唯一真源 (Single Source of Truth)
# 所有模板角色的默认行为都定义在这里
# 下游模块（segment_engine, visual_insert_engine）只读不写

# 模板 1: explainer_basic
# 用途：知识讲解、教程、结构解释视频
# 默认结构：hook(吸引开场) → explain(核心解释) → example(示例论证) → summary(总结回顾)

TEMPLATE_PRESETS = {
    "explainer_basic": {
        "display_name": "讲解类模板",
        "description": "适合知识讲解、教程、概念解释",
        "default_roles": ["hook", "explain", "example", "summary"],
        "role_defaults": {
            "hook": {
                "segment_animation_enabled": True,
                "segment_animation": "slide_up",
                "highlight_enabled": True,
                "highlight_emphasis_enabled": True,
                "emphasis_strength": 0.25,
                "default_insert_position": "top",
                "default_insert_scale": 0.6,
            },
            "explain": {
                "segment_animation_enabled": True,
                "segment_animation": "fade_in",
                "highlight_enabled": True,
                "highlight_emphasis_enabled": True,
                "emphasis_strength": 0.15,
                "default_insert_position": "center",
                "default_insert_scale": 0.72,
            },
            "example": {
                "segment_animation_enabled": True,
                "segment_animation": "zoom_in",
                "highlight_enabled": True,
                "highlight_emphasis_enabled": False,
                "emphasis_strength": 0.0,
                "default_insert_position": "center",
                "default_insert_scale": 0.8,
            },
            "summary": {
                "segment_animation_enabled": False,
                "segment_animation": "fade_in",
                "highlight_enabled": True,
                "highlight_emphasis_enabled": False,
                "emphasis_strength": 0.0,
                "default_insert_position": "center",
                "default_insert_scale": 0.65,
            },
        },
    },
    # 模板 2: product_pitch
    # 用途：产品介绍、推流、解决方案演示
    # 默认结构：pain_point(痛点) → solution(方案) → proof(证据) → call_to_action(行动)
    "product_pitch": {
        "display_name": "产品推流模板",
        "description": "适合产品介绍、卖点展示、解决方案演示",
        "default_roles": ["pain_point", "solution", "proof", "call_to_action"],
        "role_defaults": {
            "pain_point": {
                "segment_animation_enabled": True,
                "segment_animation": "slide_up",
                "highlight_enabled": True,
                "highlight_emphasis_enabled": True,
                "emphasis_strength": 0.3,
                "default_insert_position": "center",
                "default_insert_scale": 0.75,
            },
            "solution": {
                "segment_animation_enabled": True,
                "segment_animation": "zoom_in",
                "highlight_enabled": True,
                "highlight_emphasis_enabled": True,
                "emphasis_strength": 0.22,
                "default_insert_position": "center",
                "default_insert_scale": 0.8,
            },
            "proof": {
                "segment_animation_enabled": False,
                "segment_animation": "fade_in",
                "highlight_enabled": True,
                "highlight_emphasis_enabled": False,
                "emphasis_strength": 0.0,
                "default_insert_position": "center",
                "default_insert_scale": 0.7,
            },
            "call_to_action": {
                "segment_animation_enabled": True,
                "segment_animation": "slide_up",
                "highlight_enabled": True,
                "highlight_emphasis_enabled": True,
                "emphasis_strength": 0.3,
                "default_insert_position": "top",
                "default_insert_scale": 0.65,
            },
        },
    },
    # 模板 3: news_commentary
    # 用途：时事评论、新闻解读、评论视频
    # 默认结构：hook(开场) → fact(事实) → interpretation(解读) → takeaway(要点)
    "news_commentary": {
        "display_name": "评论类模板",
        "description": "适合时事评论、新闻解读、观点分享",
        "default_roles": ["hook", "fact", "interpretation", "takeaway"],
        "role_defaults": {
            "hook": {
                "segment_animation_enabled": True,
                "segment_animation": "slide_up",
                "highlight_enabled": True,
                "highlight_emphasis_enabled": True,
                "emphasis_strength": 0.2,
                "default_insert_position": "top",
                "default_insert_scale": 0.6,
            },
            "fact": {
                "segment_animation_enabled": False,
                "segment_animation": "fade_in",
                "highlight_enabled": True,
                "highlight_emphasis_enabled": False,
                "emphasis_strength": 0.0,
                "default_insert_position": "center",
                "default_insert_scale": 0.75,
            },
            "interpretation": {
                "segment_animation_enabled": True,
                "segment_animation": "zoom_in",
                "highlight_enabled": True,
                "highlight_emphasis_enabled": True,
                "emphasis_strength": 0.18,
                "default_insert_position": "center",
                "default_insert_scale": 0.72,
            },
            "takeaway": {
                "segment_animation_enabled": True,
                "segment_animation": "fade_in",
                "highlight_enabled": True,
                "highlight_emphasis_enabled": True,
                "emphasis_strength": 0.25,
                "default_insert_position": "center",
                "default_insert_scale": 0.65,
            },
        },
    },
}

# 默认模板
DEFAULT_TEMPLATE_NAME = "explainer_basic"


# ===== 接口函数 =====

def list_available_templates():
	"""返回所有可用模板列表。"""
	return list(TEMPLATE_PRESETS.keys())


def get_template_preset(template_name):
	"""
	读取模板预设完整定义。
	
	参数：
	- template_name: 模板名称
	
	返回：
	- dict，模板完整定义（包含 display_name, description, default_roles, role_defaults）
	"""
	if not template_name:
		return TEMPLATE_PRESETS.get(DEFAULT_TEMPLATE_NAME, {})
	
	template_str = str(template_name).strip().lower()
	return TEMPLATE_PRESETS.get(template_str, {})


def get_template_role_defaults(template_name, template_role):
	"""
	获取特定模板与角色的默认行为。
	
	参数：
	- template_name: 模板名称
	- template_role: 在模板中的角色名（如 "hook"、"explain" 等）
	
	返回：
	- dict，该角色在该模板中的默认行为建议
	- 如果模板或角色不存在，返回空 dict
	"""
	if not template_name or not template_role:
		return {}
	
	template_name_clean = str(template_name).strip().lower()
	template_role_clean = str(template_role).strip().lower()
	
	preset = TEMPLATE_PRESETS.get(template_name_clean)
	if not preset:
		return {}
	
	role_defaults = preset.get("role_defaults", {})
	return role_defaults.get(template_role_clean, {})


def get_template_default_roles(template_name):
	"""
	获取模板的默认角色顺序。
	
	参数：
	- template_name: 模板名称
	
	返回：
	- list，该模板的 default_roles 顺序
	- 如果模板不存在，返回空 list
	"""
	if not template_name:
		return []
	
	template_name_clean = str(template_name).strip().lower()
	preset = TEMPLATE_PRESETS.get(template_name_clean)
	if not preset:
		return []
	
	return preset.get("default_roles", [])


def is_valid_template_role(template_name, template_role):
	"""
	验证 template_role 是否在指定模板中有效。
	
	参数：
	- template_name: 模板名称
	- template_role: 角色名
	
	返回：
	- bool，role 是否在模板的 default_roles 中存在
	"""
	if not template_name or not template_role:
		return False
	
	template_name_clean = str(template_name).strip().lower()
	template_role_clean = str(template_role).strip().lower()
	
	preset = TEMPLATE_PRESETS.get(template_name_clean)
	if not preset:
		return False
	
	default_roles = preset.get("default_roles", [])
	return template_role_clean in default_roles


def validate_template_role(template_name, template_role, warn=True):
	"""
	校验 template_role，非法时打印 warning 但不报错。
	
	参数：
	- template_name: 模板名称
	- template_role: 角色名
	- warn: 是否打印 warning（默认 True）
	
	返回：
	- bool，role 是否有效
	
	说明：
	- 如果 role 有效，返回 True
	- 如果无效但 warn=True，打印一条 warning 后返回 False
	- 绝不报错，保证主流程不中断
	"""
	if is_valid_template_role(template_name, template_role):
		return True
	
	# role 无效
	if warn and template_name and template_role:
		template_name_clean = str(template_name).strip().lower()
		template_role_clean = str(template_role).strip().lower()
		print(
			f"[template] 警告：无效的 template_role='{template_role_clean}'，"
			f"已忽略，template='{template_name_clean}'"
		)
	
	return False
