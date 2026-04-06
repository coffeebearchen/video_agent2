# TextSpec-A：文字表达控制系统（最小安全版）

from typing import Any, Dict


def build_default_text_spec(style_name: str) -> Dict[str, Any]:
    """
    构建基础 TextSpec（最小版本）
    当前仅覆盖：title + highlight
    """

    base_spec = {
        "title": {
            "mode": "persistent",
        },
        "highlight": {
            "mode": "single_card",
            "duration": 3.0,
            "layout": "zh_en_stacked",
            "position": "center",
            "color": "#FFFFFF",
        },
    }

    if style_name == "personal_ip":
        base_spec["highlight"]["duration"] = 3.1
    elif style_name == "product_focus":
        base_spec["highlight"]["duration"] = 2.7
    elif style_name == "life_story":
        base_spec["highlight"]["duration"] = 3.4
    elif style_name == "ai_control_lab":
        base_spec["highlight"]["duration"] = 2.8

    return base_spec