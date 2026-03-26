import json

INPUT_FILE = "script.json"
OUTPUT_FILE = "script.json"

def build_voiceover(card_type, text):

    if card_type == "hook":
        return f"""很多人以为
自己在做选择。

但很多时候
其实是在面对风险。"""

    if card_type == "concept":
        return f"""真正拉开差距的
不是速度。

而是
谁更早看见风险。"""

    if card_type == "analogy":
        return f"""就像过河一样。

不是冲得快。

而是
每一步站得稳。"""

    if card_type == "example":
        return f"""在工作
投资
关系里。

成熟的人
都会先看代价。"""

    if card_type == "insight":
        return f"""所以成熟
不是更敢冲。

而是知道
什么代价不能乱付。"""

    return text


def main():

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    cards = data["cards"]

    for card in cards:

        card_type = card.get("type")
        text = card.get("text")

        card["voiceover"] = build_voiceover(card_type, text)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("voiceover 已更新（短视频版本）")


if __name__ == "__main__":
    main()