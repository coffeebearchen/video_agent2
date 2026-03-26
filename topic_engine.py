import json
import os
from datetime import datetime

# =========================
# 主题生成引擎（第一版骨架）
# =========================

def generate_topics(main_topic):
    """
    输入一个主题，生成多个视频选题
    当前为规则版（稳定版），后续可升级为 AI 版
    """

    topic_list = []

    # 基础拆解方式（先保证稳定）
    topic_list.append(f"{main_topic}，其实90%的人都理解错了")
    topic_list.append(f"为什么你一直搞不懂{main_topic}？")
    topic_list.append(f"{main_topic}背后的底层逻辑是什么？")
    topic_list.append(f"一个简单例子，让你彻底理解{main_topic}")
    topic_list.append(f"{main_topic}和你的人生，有什么关系？")

    return topic_list


def save_topics(topics):
    """
    保存生成的主题到文件
    """

    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = os.path.join(output_dir, f"topics_{timestamp}.json")

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump({
            "generated_at": timestamp,
            "topics": topics
        }, f, ensure_ascii=False, indent=2)

    return file_path


def main():
    print("=== 主题生成模块（Topic Engine）===")

    main_topic = input("请输入一个主题：")

    if not main_topic.strip():
        print("❌ 主题不能为空")
        return

    topics = generate_topics(main_topic)

    print("\n生成的选题：\n")
    for i, t in enumerate(topics, 1):
        print(f"{i}. {t}")

    file_path = save_topics(topics)

    print(f"\n✅ 已保存到：{file_path}")


if __name__ == "__main__":
    main()