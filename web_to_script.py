# -*- coding: utf-8 -*-
"""
web_to_script.py

【脚本生成模块】

作用：
1. 读取主链锁定的 current_capture_path.txt
2. 读取本次网页 capture 目录中的 title.txt
3. 调用 DeepSeek 生成 script.json

注意：
- 只读取 current_capture_path.txt
- 不再 fallback 到旧目录
- 统一强制使用 utf-8 读取文本
"""

import os
import json
from pathlib import Path

import requests
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
CURRENT_CAPTURE_PATH_FILE = BASE_DIR / "current_capture_path.txt"
SCRIPT_PATH = BASE_DIR / "script.json"
DEBUG_RESPONSE_PATH = BASE_DIR / "output" / "deepseek_response_debug.json"


def load_env():
    """
    显式加载 .env，避免只依赖系统环境变量。
    """
    env_path = BASE_DIR / ".env"
    load_dotenv(dotenv_path=env_path, override=False)


def get_capture_path() -> Path:
    """
    读取主链锁定的 capture_path。
    """
    if not CURRENT_CAPTURE_PATH_FILE.exists():
        raise RuntimeError("❌ 缺少 current_capture_path.txt，请先运行 python run_pipeline_web.py")

    path_text = CURRENT_CAPTURE_PATH_FILE.read_text(encoding="utf-8").strip()
    if not path_text:
        raise RuntimeError("❌ current_capture_path.txt 为空，请重新运行主链")

    folder = Path(path_text)
    if not folder.exists() or not folder.is_dir():
        raise RuntimeError(f"❌ capture_path 不存在：{folder}")

    print(f"📌 使用锁定 capture_path：{folder}")
    return folder


def load_title(folder: Path) -> str:
    """
    读取 title.txt，统一使用 utf-8。
    """
    title_file = folder / "title.txt"
    if not title_file.exists():
        raise RuntimeError(f"❌ 找不到 title.txt：{title_file}")

    try:
        title = title_file.read_text(encoding="utf-8").strip()
    except UnicodeDecodeError as e:
        raise RuntimeError(
            f"❌ title.txt 编码读取失败：{title_file}\n"
            "当前要求 title.txt 使用 UTF-8 编码保存。"
        ) from e

    if not title:
        raise RuntimeError(f"❌ title.txt 为空：{title_file}")

    return title


def save_debug_response(data):
    DEBUG_RESPONSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(DEBUG_RESPONSE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"📝 已保存原始响应到：{DEBUG_RESPONSE_PATH}")


def extract_json_from_text(content: str):
    """
    从模型返回文本中提取 JSON。
    """
    start = content.find("{")
    end = content.rfind("}") + 1

    if start == -1 or end <= 0:
        raise RuntimeError("❌ DeepSeek 返回内容中没有找到 JSON 结构")

    json_text = content[start:end]

    try:
        return json.loads(json_text)
    except json.JSONDecodeError as e:
        raise RuntimeError("❌ DeepSeek 返回的 JSON 解析失败") from e


def generate_script(title: str):
    """
    调用 DeepSeek 生成 5 段脚本。
    """
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise RuntimeError(
            "❌ 没有读取到 DEEPSEEK_API_KEY。\n"
            "请检查 .env 文件，或在当前终端临时 set DEEPSEEK_API_KEY=你的key"
        )

    prompt = f"""
请基于以下网页标题，生成一个短视频脚本（5段）：

标题：{title}

要求：
1. 用通俗易懂的中文解释
2. 每段一句话
3. 不要空话，不要太虚
4. 结构固定为：
   - hook
   - concept
   - explanation
   - analogy
   - conclusion

严格输出 JSON，不要加解释，不要加 markdown 代码块：

{{
  "cards": [
    {{"type": "hook", "text": "..."}} ,
    {{"type": "concept", "text": "..."}} ,
    {{"type": "explanation", "text": "..."}} ,
    {{"type": "analogy", "text": "..."}} ,
    {{"type": "conclusion", "text": "..."}}
  ]
}}
""".strip()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7,
    }

    print("生成脚本中（DeepSeek）...")
    print("正在请求 DeepSeek...")
    print("模型：deepseek-chat")
    print(f"API Key 已读取：{'是' if bool(api_key) else '否'}")

    response = requests.post(
        "https://api.deepseek.com/v1/chat/completions",
        headers=headers,
        json=payload,
        timeout=120
    )

    print(f"HTTP 状态码：{response.status_code}")

    try:
        result = response.json()
    except Exception as e:
        raise RuntimeError(f"❌ DeepSeek 返回不是 JSON：{response.text}") from e

    save_debug_response(result)

    if "choices" not in result:
        raise RuntimeError(
            "❌ DeepSeek 返回中没有 choices 字段。\n"
            f"原始返回：{json.dumps(result, ensure_ascii=False, indent=2)}"
        )

    content = result["choices"][0]["message"]["content"]
    print("DeepSeek 返回内容：")
    print(content)

    return extract_json_from_text(content)


def main():
    load_env()

    print("读取网页截图...")

    folder = get_capture_path()
    print(f"使用目录：{folder}")

    title = load_title(folder)
    print(f"标题：{title}")

    script = generate_script(title)

    with open(SCRIPT_PATH, "w", encoding="utf-8") as f:
        json.dump(script, f, ensure_ascii=False, indent=2)

    print(f"✅ script.json 已生成：{SCRIPT_PATH}")


if __name__ == "__main__":
    main()