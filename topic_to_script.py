import json
import os
import glob

# =========================================
# topic_to_script.py（自动选题版本）
# 功能：
# 1. 自动读取最新 topics_xxx.json
# 2. 显示候选选题
# 3. 允许输入序号选择（默认1）
# 4. 自动生成 script.json
# =========================================


def find_latest_topics_file():
    files = glob.glob("output/topics_*.json")
    if not files:
        return None
    return max(files, key=os.path.getmtime)


def load_topics(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("topics", [])


def build_cards_from_topic(topic: str):
    topic = topic.strip()

    return [
        {
            "type": "hook",
            "text": f"{topic}，其实很多人第一步就想错了。"
        },
        {
            "type": "concept",
            "text": f"表面上看，{topic}只是一个结果，但背后往往有更深的原因。"
        },
        {
            "type": "analogy",
            "text": f"你可以把{topic}理解成一个信号，它不是突然出现，而是很多力量共同推动出来的。"
        },
        {
            "type": "insight",
            "text": f"真正重要的，不只是知道{topic}是什么，而是理解它为什么会发生。"
        },
        {
            "type": "ending",
            "text": f"当你开始从结构上看{topic}，很多原来看不懂的问题，就会慢慢变清楚。"
        }
    ]


def build_script(topic: str):
    return {
        "title": topic,
        "cards": build_cards_from_topic(topic)
    }


def save_script(script_data):
    with open("script.json", "w", encoding="utf-8") as f:
        json.dump(script_data, f, ensure_ascii=False, indent=2)


def save_debug(script_data):
    os.makedirs("output", exist_ok=True)
    path = os.path.join("output", "script_from_topic_preview.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(script_data, f, ensure_ascii=False, indent=2)
    return path


def main():
    print("=== Topic → Script 自动选题模块 ===")

    latest_file = find_latest_topics_file()

    if not latest_file:
        print("❌ 未找到 topics 文件，请先运行 topic_engine.py")
        return

    print(f"\n读取文件：{latest_file}")

    topics = load_topics(latest_file)

    if not topics:
        print("❌ topics 文件为空")
        return

    print("\n可选主题：\n")
    for i, t in enumerate(topics, 1):
        print(f"{i}. {t}")

    choice = input("\n请输入序号（默认1）：").strip()

    if not choice:
        index = 0
    else:
        try:
            index = int(choice) - 1
        except:
            print("❌ 输入错误，默认选1")
            index = 0

    if index < 0 or index >= len(topics):
        print("❌ 超出范围，默认选1")
        index = 0

    selected_topic = topics[index]

    print(f"\n✅ 已选择：{selected_topic}")

    script_data = build_script(selected_topic)

    save_script(script_data)
    debug_path = save_debug(script_data)

    print("\n✅ script.json 已生成")
    print(f"✅ 预览文件：{debug_path}")
    print("\n下一步运行：")
    print("python run_pipeline.py")


if __name__ == "__main__":
    main()