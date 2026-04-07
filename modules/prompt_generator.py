# 文件名：modules/prompt_generator.py
# 说明：基于style的AI内容生成（最小实现版）
# 优先级：人工输入 > AI生成 > 规则修正

STYLE_PROMPTS = {
    "creator_clean": """
你是一个极简的信息提示者。
不带情绪，句子短，信息压缩，不解释。
""",

    "product_focus": """
你是一个产品表达者。
强调结果和效率，直接指出问题和核心价值。
""",

    "life_story": """
你是一个讲故事的人。
有情绪，有时间感（后来/慢慢/才发现），有转折。
""",

    "ai_control_lab": """
你是一个系统分析者。
冷静、结构化，指出问题本质和变量关系。
""",

    "personal_ip": """
你是一个有强烈观点的人。
直接、有立场、有判断，表达要有冲击力。
"""
}


BASE_PROMPT = """
你是一个短视频内容表达助手。

任务：
根据输入内容，生成：
1）标题（Title）
2）重点表达（Highlight）

要求：
- 不解释
- 不多写
- 简洁
- 只输出两行：
Title: ...
Highlight: ...

内容：
{input_text}

风格：
{style_prompt}
"""


def generate_by_prompt(input_text, style_name, call_ai_func):
    """
    基于style的AI内容生成
    
    参数：
        input_text: 输入文本
        style_name: 风格名称（必须在STYLE_PROMPTS中）
        call_ai_func: 外部传入的AI调用函数（避免绑定具体模型）
    
    返回：
        成功：{"title": "...", "highlight": "..."}
        失败：None（回退到默认值）
    """

    if style_name not in STYLE_PROMPTS:
        return None

    prompt = BASE_PROMPT.format(
        input_text=input_text,
        style_prompt=STYLE_PROMPTS[style_name]
    )

    try:
        result = call_ai_func(prompt)

        # 简单解析返回结果
        title = ""
        highlight = ""

        for line in result.split("\n"):
            if line.lower().startswith("title"):
                title = line.split(":", 1)[-1].strip()
            elif line.lower().startswith("highlight"):
                highlight = line.split(":", 1)[-1].strip()

        if not title or not highlight:
            return None

        return {
            "title": title,
            "highlight": highlight
        }

    except Exception as e:
        print(f"[PROMPT_GENERATOR] AI调用异常：{e}")
        return None
