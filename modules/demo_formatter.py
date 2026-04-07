# -*- coding: utf-8 -*-
"""
文件名：demo_formatter.py
作用说明：
1. 将产品 demo 的多风格结果格式化为用户可直接阅读的文本
2. 不展示技术字段，不展示 debug 内容
3. 强调标题与视频脚本结构的直观感知
"""


STYLE_LABELS = {
    "knowledge": "知识型",
    "authority": "老板型",
    "story": "故事型",
    "ads": "广告型",
    "product": "产品型",
}


def format_demo_results(results: list[dict]) -> str:
    """将多风格 demo 结果格式化为用户感输出。"""
    sections: list[str] = []

    for item in results:
        style_mode = str(item.get("style_mode", "") or "unknown").strip()
        style_label = STYLE_LABELS.get(style_mode, style_mode)
        preview = item.get("preview", {}) if isinstance(item.get("preview"), dict) else {}
        headline = str(preview.get("headline", "") or "").strip()
        scenes = preview.get("scenes", []) if isinstance(preview.get("scenes"), list) else []

        lines = [
            "=" * 30,
            f"风格：{style_mode}（{style_label}）",
            "-" * 30,
            "",
            "标题：",
            headline,
            "",
            "视频脚本：",
        ]

        if not scenes:
            lines.append("1. 内容待生成")
        else:
            for index, scene in enumerate(scenes, start=1):
                scene_text = str(scene.get("text", "") if isinstance(scene, dict) else scene).strip()
                lines.append(f"{index}. {scene_text or '内容待生成'}")

        sections.append("\n".join(lines))

    return "\n\n".join(sections)