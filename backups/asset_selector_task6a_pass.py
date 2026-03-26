# -*- coding: utf-8 -*-
"""
asset_selector.py - TASK 6A 通过版本

【最小素材匹配器】

作用：
根据 scene 文本，返回最合适的素材路径

当前版本：硬编码关键词版本（最小实现）
- 不接主链
- 不修改其他模块
- 独立验证功能

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

# 规则 1：网页/浏览器类
BROWSER_KEYWORDS = [
    r"网页",
    r"浏览器",
    r"网站",
    r"页面",
    r"打开网页",
    r"网址",
    r"HTTP",
]

# 规则 2：安全/验证类
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

# 规则 3：门禁/保安/小区类
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

# 规则 4：冲突/战争/袭击类
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
    
    优先级：
    1. 冲突/战争/袭击类
    2. 安全/验证类
    3. 门禁/保安/小区类
    4. 网页/浏览器类（泛词类）
    
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
    
    # 检查规则 3：门禁/保安/小区类（优先级 3）
    if _match_keywords(text, GATE_KEYWORDS):
        keyword = _get_first_matching_keyword(text, GATE_KEYWORDS)
        return {
            "matched": True,
            "asset_type": "image",
            "asset_file": "assets/library/gate.png",
            "keyword": keyword,
            "reason": "检测到门禁/保安/小区相关关键词"
        }
    
    # 检查规则 4：网页/浏览器类（优先级 4：泛词类，最后检查）
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
