# 文件名：modules/style_selector.py
# 说明：根据输入内容自动选择style（最小实现版）
# 优先级：人工指定style > 自动选style > 默认style

STYLE_KEYWORDS = {
    "creator_clean": [
        "提示", "总结", "方法", "核心", "信息", "重点", "步骤", "关键", "要点"
    ],
    "product_focus": [
        "效率", "成本", "产能", "稳定", "产品", "性能", "解决方案", "价值", "快速", "低",
        "传统", "不够", "太低", "真正的问题是效率"
    ],
    "life_story": [
        "后来", "慢慢", "才发现", "焦虑", "改变", "人生", "经历", "情绪", "不是不努力",
        "而是", "发现", "很多"
    ],
    "ai_control_lab": [
        "系统", "结构", "变量", "约束", "闭环", "逻辑", "诊断", "分析", "本质", "关系"
    ],
    "personal_ip": [
        "真正的问题", "你必须知道", "观点", "判断", "本质", "立场", "关键不是", "你必须",
        "真正", "方向", "不是"
    ],
}

DEFAULT_STYLE = "creator_clean"


def select_style_by_rules(input_text: str) -> str:
    """
    根据关键词规则自动选择style。
    
    算法：
    1. 遍历每个style的关键词列表
    2. 计算input_text中匹配的关键词数量
    3. 返回得分最高的style；如果无匹配，返回DEFAULT_STYLE
    
    参数：
        input_text: 输入文本
    
    返回：
        匹配的style名称 或 DEFAULT_STYLE
    """
    text = str(input_text or "").strip()
    if not text:
        return DEFAULT_STYLE

    scores = {style: 0 for style in STYLE_KEYWORDS}

    for style, keywords in STYLE_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                scores[style] += 1

    best_style = max(scores, key=scores.get)
    if scores[best_style] <= 0:
        return DEFAULT_STYLE
    
    return best_style


def select_style(input_text: str, call_ai_func=None) -> str:
    """
    自动选择style。
    
    V1实现：
    - 如果没有提供AI选择器，走规则匹配
    - 如果提供了AI选择器，可在未来升级为AI驱动
    
    参数：
        input_text: 输入文本
        call_ai_func: 可选的AI选择函数（未来扩展）
    
    返回：
        选中的style名称
    """
    if call_ai_func is None:
        return select_style_by_rules(input_text)

    try:
        result = call_ai_func(input_text).strip()
        if result in STYLE_KEYWORDS:
            return result
    except Exception as e:
        print(f"[STYLE_SELECTOR] AI选择失败：{e}，降级到规则匹配")

    return select_style_by_rules(input_text)
