# -*- coding: utf-8 -*-
"""
asset_selector.py - TASK 6C 通过版本

【最小素材匹配器 - 扩展规则库】

作用：
根据 scene 文本，返回最合适的素材路径

当前版本：硬编码关键词版本（TASK 6C 扩展库）
- TASK 6C：添加了城市、美食、金融、科技四大类规则
- 规则库从4类扩展到8类
- 优先级基于语义强度排序
- 保持接口与返回结构不变

返回格式：
{
  "matched": True/False,
  "asset_type": "image" | "text_card",
  "asset_file": "资源文件路径或空字符串",
  "keyword": "命中的关键词",
  "reason": "匹配理由"
}
"""

import re
from typing import Dict, Any


# ===== 关键词规则定义 =====
# TASK 6C：按优先级排序，强语义优先于泛词

# 规则 1：冲突/战争/袭击类（优先级 1 - 强语义）
CONFLICT_KEYWORDS = [
    r"冲突",
    r"战争",
    r"袭击",
    r"以色列",
    r"伊朗",
    r"炸弹",
    r"轰炸",
    r"军事",
]

# 规则 2：安全/验证类（优先级 2 - 强语义）
SECURITY_KEYWORDS = [
    r"安全",
    r"验证",
    r"检查",
    r"合法",
    r"风险",
    r"确认",
    r"身份",
    r"验证码",
]

# 规则 3：金融/货币/债券/比特币类（优先级 3 - 强语义）
FINANCE_KEYWORDS = [
    r"金融",
    r"国债",
    r"利率",
    r"债券",
    r"收益率",
    r"比特币",
    r"数字货币",
    r"数字资产",
    r"货币",
    r"财政",
    r"交易",
]

# 规则 4：科技/AI/软件/应用类（优先级 4 - 强语义）
TECH_KEYWORDS = [
    r"科技",
    r"AI",
    r"人工智能",
    r"软件",
    r"应用",
    r"平台",
    r"手机",
    r"工具",
    r"模型",
    r"算法",
    r"开发",
    r"代码",
    r"编程",
]

# 规则 5：门禁/保安/小区类（优先级 5 - 中等语义）
GATE_KEYWORDS = [
    r"保安",
    r"门禁",
    r"小区",
    r"身份",
    r"放行",
    r"进入",
    r"门卡",
    r"进小区",
]

# 规则 6：城市/旅游/地方文化类（优先级 6 - 中等语义）
CITY_KEYWORDS = [
    r"城市",
    r"旅游",
    r"古城",
    r"街头",
    r"巷子",
    r"茶馆",
    r"文化",
    r"地方",
    r"风景",
    r"景观",
    r"名胜",
    r"古迹",
]

# 规则 7：美食/生活/市井类（优先级 7 - 泛词但有价值）
FOOD_KEYWORDS = [
    r"美食",
    r"早餐",
    r"小吃",
    r"汤",
    r"茶",
    r"市井",
    r"生活",
    r"早市",
    r"夜市",
    r"餐馆",
    r"烹饪",
    r"做饭",
    r"烟火",
    r"菜肴",
]

# 规则 8：网页/浏览器类（优先级 8 - 泛词，最后检查）
BROWSER_KEYWORDS = [
    r"网页",
    r"浏览器",
    r"网站",
    r"页面",
    r"打开网页",
    r"网址",
    r"HTTP",
]


def _match_keywords(text: str, keywords: list) -> bool:
    """
    检查文本是否包含任何关键词
    
    参数：
        text: 输入文本
        keywords: 关键词列表（正则表达式）
    
    返回：
        True 如果至少匹配一个关键词
    """
    for keyword in keywords:
        if re.search(keyword, text):
            return True
    return False


def _get_first_matching_keyword(text: str, keywords: list) -> str:
    """
    获取第一个匹配的关键词
    
    参数：
        text: 输入文本
        keywords: 关键词列表（正则表达式）
    
    返回：
        第一个匹配的关键词，或空字符串
    """
    for keyword in keywords:
        match = re.search(keyword, text)
        if match:
            return match.group(0)
    return ""


def select_asset_for_text(text: str) -> Dict[str, Any]:
    """
    根据文本匹配素材
    
    逻辑：
    1. 按优先级检查各类关键词（强语义优先）
    2. 命中则返回对应路径
    3. 都不命中则返回 fallback
    
    优先级（TASK 6C）：
    1. 冲突/战争/袭击类
    2. 安全/验证类
    3. 金融/货币/债券/比特币类
    4. 科技/AI/软件/应用类
    5. 门禁/保安/小区类
    6. 城市/旅游/地方文化类
    7. 美食/生活/市井类
    8. 网页/浏览器类（泛词类）
    9. 默认 fallback
    
    参数：
        text: 场景文本
    
    返回：
        Dict containing:
        - matched: 是否匹配（bool）
        - asset_type: "image" 或 "text_card"
        - asset_file: 资源文件路径或空字符串
        - keyword: 命中的关键词
        - reason: 简短说明
    """
    
    # 检查规则 1：冲突/战争/袭击类（优先级 1）
    if _match_keywords(text, CONFLICT_KEYWORDS):
        keyword = _get_first_matching_keyword(text, CONFLICT_KEYWORDS)
        return {
            "matched": True,
            "asset_type": "image",
            "asset_file": "assets/library/conflict.png",
            "keyword": keyword,
            "reason": "检测到冲突/战争/袭击相关关键词"
        }
    
    # 检查规则 2：安全/验证类（优先级 2）
    if _match_keywords(text, SECURITY_KEYWORDS):
        keyword = _get_first_matching_keyword(text, SECURITY_KEYWORDS)
        return {
            "matched": True,
            "asset_type": "image",
            "asset_file": "assets/library/security.png",
            "keyword": keyword,
            "reason": "检测到安全/验证相关关键词"
        }
    
    # 检查规则 3：金融/货币/债券/比特币类（优先级 3 - TASK 6C 新增）
    if _match_keywords(text, FINANCE_KEYWORDS):
        keyword = _get_first_matching_keyword(text, FINANCE_KEYWORDS)
        return {
            "matched": True,
            "asset_type": "image",
            "asset_file": "assets/library/finance.png",
            "keyword": keyword,
            "reason": "检测到金融/货币/债券相关关键词"
        }
    
    # 检查规则 4：科技/AI/软件/应用类（优先级 4 - TASK 6C 新增）
    if _match_keywords(text, TECH_KEYWORDS):
        keyword = _get_first_matching_keyword(text, TECH_KEYWORDS)
        return {
            "matched": True,
            "asset_type": "image",
            "asset_file": "assets/library/tech.png",
            "keyword": keyword,
            "reason": "检测到科技/AI/软件相关关键词"
        }
    
    # 检查规则 5：门禁/保安/小区类（优先级 5）
    if _match_keywords(text, GATE_KEYWORDS):
        keyword = _get_first_matching_keyword(text, GATE_KEYWORDS)
        return {
            "matched": True,
            "asset_type": "image",
            "asset_file": "assets/library/gate.png",
            "keyword": keyword,
            "reason": "检测到门禁/保安/小区相关关键词"
        }
    
    # 检查规则 6：城市/旅游/地方文化类（优先级 6 - TASK 6C 新增）
    if _match_keywords(text, CITY_KEYWORDS):
        keyword = _get_first_matching_keyword(text, CITY_KEYWORDS)
        return {
            "matched": True,
            "asset_type": "image",
            "asset_file": "assets/library/city.png",
            "keyword": keyword,
            "reason": "检测到城市/旅游/地方文化相关关键词"
        }
    
    # 检查规则 7：美食/生活/市井类（优先级 7 - TASK 6C 新增）
    if _match_keywords(text, FOOD_KEYWORDS):
        keyword = _get_first_matching_keyword(text, FOOD_KEYWORDS)
        return {
            "matched": True,
            "asset_type": "image",
            "asset_file": "assets/library/food.png",
            "keyword": keyword,
            "reason": "检测到美食/生活/市井相关关键词"
        }
    
    # 检查规则 8：网页/浏览器类（优先级 8：泛词类，最后检查）
    if _match_keywords(text, BROWSER_KEYWORDS):
        keyword = _get_first_matching_keyword(text, BROWSER_KEYWORDS)
        return {
            "matched": True,
            "asset_type": "image",
            "asset_file": "assets/library/browser.png",
            "keyword": keyword,
            "reason": "检测到网页/浏览器相关关键词"
        }
    
    # 都不匹配：返回 fallback
    return {
        "matched": False,
        "asset_type": "text_card",
        "asset_file": "",
        "keyword": "",
        "reason": "未匹配到特定关键词，使用默认 text_card fallback"
    }


if __name__ == "__main__":
    # 快速测试
    test_texts = [
        "这其实是网站为了安全，在检查你的访问是否合法。",
        "就像进小区前，保安会看一眼你的门禁卡。",
        "伊朗和以色列互相袭击了对方的天然气设施。",
        "今天我们打开一个网页，看看这个页面的结构。",
        "这是一个普通说明，没有特定关键词。",
    ]
    
    for text in test_texts:
        result = select_asset_for_text(text)
        print(f"\n文本：{text}")
        print(f"结果：{result}")
