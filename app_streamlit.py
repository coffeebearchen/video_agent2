# -*- coding: utf-8 -*-
"""
app_streamlit.py

【Minimal UI Layer｜Streamlit 最小产品界面】

作用：
1. 在浏览器中接收 text / url 输入
2. 调用 run_pipeline_user 的统一流程
3. 展示生成状态、输出路径、文件大小与视频预览

边界：
- 不修改现有主链逻辑
- 不自动开启 patch apply
- 不依赖复杂前端框架
- 仅做最小可用浏览器入口
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import streamlit as st

from input_handler import InputHandler
import run_pipeline_user


PROJECT_ROOT = Path(__file__).resolve().parent
INPUT_JSON_FILE = PROJECT_ROOT / "input.json"


def save_standard_input(input_data: Dict[str, Any]) -> None:
    """保存标准 input.json，保持与 CLI 入口一致。"""
    INPUT_JSON_FILE.write_text(
        json.dumps(input_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def render_header() -> None:
    """渲染页面头部。"""
    st.title("VIDEO_AGENT 最小演示版")
    st.caption("输入文本或网页链接，自动生成视频")
    st.markdown("---")


def render_input_area() -> tuple[Optional[Dict[str, Any]], bool]:
    """渲染输入区域并返回标准输入结构与点击状态。"""
    handler = InputHandler()

    st.subheader("输入区域")
    input_type = st.radio(
        "请选择输入类型",
        ["text", "url"],
        horizontal=True,
    )

    if input_type == "text":
        content = st.text_area(
            "请输入文本内容",
            height=220,
            placeholder="例如：比特币为什么会涨？请用通俗的方式解释。",
        )
    else:
        content = st.text_input(
            "请输入网页链接",
            placeholder="例如：https://example.com/article",
        )

    start_generation = st.button("一键生成视频", type="primary", use_container_width=True)
    if not start_generation:
        return None, False

    normalized_content = str(content or "").strip()
    if not normalized_content:
        st.error("请输入内容后再生成。")
        return None, True

    try:
        if input_type == "text":
            input_data = handler.parse_text(normalized_content, source="streamlit")
        else:
            input_data = handler.parse_url(normalized_content, source="streamlit")
    except Exception as error:
        st.error(f"输入校验失败：{error}")
        return None, True

    input_data.setdefault("meta", {})
    input_data["meta"]["ui_timestamp"] = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    return input_data, True


def run_generation(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """执行统一视频生成流程。"""
    save_standard_input(input_data)
    video_path = run_pipeline_user.run_pipeline(input_data)

    if not video_path.exists():
        raise FileNotFoundError(f"生成完成后未找到视频文件：{video_path}")

    file_size = video_path.stat().st_size
    if file_size <= 0:
        raise ValueError(f"视频文件为空：{video_path}")

    return {
        "success": True,
        "video_path": video_path,
        "video_size": file_size,
    }


def render_result(result: Optional[Dict[str, Any]], error_message: str) -> None:
    """渲染生成结果区域。"""
    st.markdown("---")
    st.subheader("生成结果")

    if error_message:
        st.error(error_message)
        return

    if not result:
        st.info("点击上方按钮后，这里会展示生成结果。")
        return

    video_path = Path(result["video_path"])
    st.success("视频生成成功")
    st.write(f"视频路径：{video_path}")
    st.write(f"视频大小：{result['video_size']} bytes")

    try:
        video_bytes = video_path.read_bytes()
        st.video(video_bytes)
    except Exception as error:
        st.warning(f"视频文件已生成，但页面预览失败：{error}")


def main() -> None:
    """Streamlit 页面主入口。"""
    st.set_page_config(
        page_title="VIDEO_AGENT 最小演示版",
        page_icon="🎬",
        layout="centered",
    )

    if "result" not in st.session_state:
        st.session_state.result = None
    if "error_message" not in st.session_state:
        st.session_state.error_message = ""

    render_header()
    input_data, submitted = render_input_area()

    if submitted and input_data is not None:
        st.session_state.result = None
        st.session_state.error_message = ""
        with st.spinner("正在生成视频，请稍候..."):
            try:
                st.session_state.result = run_generation(input_data)
            except Exception as error:
                st.session_state.error_message = f"生成失败：{error}"

    render_result(st.session_state.result, st.session_state.error_message)


if __name__ == "__main__":
    main()