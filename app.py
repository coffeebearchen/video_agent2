# -*- coding: utf-8 -*-
"""
app.py

【本地视频自动生成面板 V2】

作用：
1. 支持 URL / TEXT / 使用现有 input.json 三种输入方式
2. 将输入内容写入 input.json
3. 调用 run_pipeline_web.py 执行主链
4. 在页面中显示运行日志
5. 尽量不改变现有主链，只做本地控制面板

运行方式：
streamlit run app.py
"""

import json
import hashlib
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
INPUT_JSON_PATH = BASE_DIR / "input.json"
OUTPUT_VIDEO_PATH = BASE_DIR / "output" / "video.mp4"


def load_input_json():
    """读取现有 input.json"""
    if not INPUT_JSON_PATH.exists():
        return None

    try:
        return json.loads(INPUT_JSON_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        return {"_error": f"读取 input.json 失败：{str(e)}"}


def save_input_json(input_type: str, content: str):
    """保存 input.json"""
    normalized_content = content.strip()
    data = {
        "type": input_type,
        "content": normalized_content,
        "meta": {
            "source": "streamlit",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "checksum": hashlib.md5(normalized_content.encode("utf-8")).hexdigest(),
        }
    }
    INPUT_JSON_PATH.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    return data


def run_main_pipeline():
    """
    执行主链：
    python run_pipeline_web.py
    """
    cmd = [sys.executable, "run_pipeline_web.py"]

    process = subprocess.Popen(
        cmd,
        cwd=str(BASE_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )

    logs = []
    if process.stdout is not None:
        for line in process.stdout:
            logs.append(line.rstrip("\n"))

    return_code = process.wait()
    return return_code, logs


# ==========================
# Streamlit 页面
# ==========================
st.set_page_config(page_title="视频自动生成面板 V2", page_icon="🎬", layout="wide")

st.title("🎬 视频自动生成面板 V2")
st.caption("当前面板已支持 URL / TEXT / 使用现有 input.json 三种方式进入主链")

st.markdown("---")

# 初始化 session
if "run_logs" not in st.session_state:
    st.session_state.run_logs = []

if "last_saved_data" not in st.session_state:
    st.session_state.last_saved_data = None

# 读取现有 input.json
existing_input = load_input_json()

# A. 输入模式
st.subheader("A. 输入模式选择")

mode = st.radio(
    "请选择输入方式：",
    ["URL 模式（直接运行）", "TEXT 模式（直接运行）", "使用现有 input.json"],
    index=0,
)

st.markdown("---")

# B. 输入内容
st.subheader("B. 输入内容")

input_type = None
content = ""

if mode == "URL 模式（直接运行）":
    st.info("当前模式：输入网页 URL，保存到 input.json，并直接调用主链运行。")
    input_type = "url"
    content = st.text_input(
        "请输入网页 URL",
        placeholder="例如：https://www.example.com/article/123"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 保存为 input.json", use_container_width=True):
            if not content.strip():
                st.error("URL 不能为空")
            else:
                data = save_input_json(input_type, content)
                st.session_state.last_saved_data = data
                st.success("✅ 已保存 URL 到 input.json")

    with col2:
        if st.button("🚀 保存并运行主链", type="primary", use_container_width=True):
            if not content.strip():
                st.error("URL 不能为空")
            else:
                data = save_input_json(input_type, content)
                st.session_state.last_saved_data = data
                st.info("正在运行主链，请稍候...")
                return_code, logs = run_main_pipeline()
                st.session_state.run_logs = logs
                if return_code == 0:
                    st.success("✅ 主链运行完成")
                else:
                    st.error(f"❌ 主链运行失败，返回码：{return_code}")

elif mode == "TEXT 模式（直接运行）":
    st.success("当前模式：TEXT 已支持直接进入主链运行。")
    st.caption("建议输入 1～3 段表达完整的中文文案，用于自动生成 script / scene / tts / video。")

    input_type = "text"
    default_text = ""
    if isinstance(existing_input, dict) and existing_input.get("type") == "text":
        default_text = existing_input.get("content", "")

    content = st.text_area(
        "请输入文本内容（最少 10 个字符）",
        value=default_text,
        height=220,
        placeholder="例如：美联储维持利率不变，但市场真正关注的不是现在，而是未来的方向……"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("💾 保存为 input.json ", use_container_width=True):
            if len(content.strip()) < 10:
                st.error("文本内容太短，至少需要 10 个字符")
            else:
                data = save_input_json(input_type, content)
                st.session_state.last_saved_data = data
                st.success("✅ 已保存 TEXT 到 input.json")

    with col2:
        if st.button("🚀 保存并运行主链 ", type="primary", use_container_width=True):
            if len(content.strip()) < 10:
                st.error("文本内容太短，至少需要 10 个字符")
            else:
                data = save_input_json(input_type, content)
                st.session_state.last_saved_data = data
                st.info("正在运行 TEXT → VIDEO 主链，请稍候...")
                return_code, logs = run_main_pipeline()
                st.session_state.run_logs = logs
                if return_code == 0:
                    st.success("✅ TEXT 主链运行完成")
                else:
                    st.error(f"❌ 主链运行失败，返回码：{return_code}")

else:
    st.info("当前模式：读取并使用现有 input.json。你可以查看、编辑、保存，再直接运行。")

    if existing_input is None:
        st.warning("当前目录下还没有 input.json")
    elif isinstance(existing_input, dict) and "_error" in existing_input:
        st.error(existing_input["_error"])
    else:
        existing_type = existing_input.get("type", "")
        existing_content = existing_input.get("content", "")

        input_type = st.selectbox(
            "input.json 的类型",
            ["url", "text"],
            index=0 if existing_type == "url" else 1
        )

        content = st.text_area(
            "input.json 的内容",
            value=existing_content,
            height=220
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("💾 更新当前 input.json", use_container_width=True):
                if input_type == "url" and not content.strip():
                    st.error("URL 不能为空")
                elif input_type == "text" and len(content.strip()) < 10:
                    st.error("文本内容太短，至少需要 10 个字符")
                else:
                    data = save_input_json(input_type, content)
                    st.session_state.last_saved_data = data
                    st.success("✅ 已更新 input.json")

        with col2:
            if st.button("🚀 使用当前 input.json 运行", type="primary", use_container_width=True):
                if input_type == "url" and not content.strip():
                    st.error("URL 不能为空")
                elif input_type == "text" and len(content.strip()) < 10:
                    st.error("文本内容太短，至少需要 10 个字符")
                else:
                    data = save_input_json(input_type, content)
                    st.session_state.last_saved_data = data
                    st.info("正在按当前 input.json 运行主链，请稍候...")
                    return_code, logs = run_main_pipeline()
                    st.session_state.run_logs = logs
                    if return_code == 0:
                        st.success("✅ 主链运行完成")
                    else:
                        st.error(f"❌ 主链运行失败，返回码：{return_code}")

st.markdown("---")

# 当前 input.json 预览
st.subheader("C. 当前 input.json 预览")

latest_data = st.session_state.last_saved_data
if latest_data:
    st.code(json.dumps(latest_data, ensure_ascii=False, indent=2), language="json")
elif existing_input and isinstance(existing_input, dict) and "_error" not in existing_input:
    st.code(json.dumps(existing_input, ensure_ascii=False, indent=2), language="json")
else:
    st.caption("当前还没有可预览的 input.json")

st.markdown("---")

# 日志区
st.subheader("D. 运行日志")

if st.session_state.run_logs:
    log_text = "\n".join(st.session_state.run_logs)
    st.text_area("主链输出日志", value=log_text, height=360)
else:
    st.caption("还没有运行日志。点击上面的“保存并运行主链”后，这里会显示输出。")

st.markdown("---")

# 输出区
st.subheader("E. 输出结果")

if OUTPUT_VIDEO_PATH.exists():
    st.success(f"检测到输出文件：{OUTPUT_VIDEO_PATH}")
    st.caption("如果视频较大，Streamlit 内嵌播放可能偏慢；但文件已经生成。")
else:
    st.caption("当前还没有检测到 output/video.mp4")

st.markdown("---")
st.caption("本面板定位：本地安全轻面板，只做输入、保存、运行与日志显示；不改主链结构。")