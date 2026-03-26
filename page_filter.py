import requests
from bs4 import BeautifulSoup

def is_good_page(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        res = requests.get(url, headers=headers, timeout=10)
        if res.status_code != 200:
            return False, "请求失败"

        soup = BeautifulSoup(res.text, "html.parser")

        # 1️⃣ 标题
        title = soup.title.string.strip() if soup.title else ""
        title_len = len(title)

        # 2️⃣ 段落
        paragraphs = soup.find_all("p")
        paragraph_count = len(paragraphs)

        # 3️⃣ 正文长度
        text = " ".join([p.get_text().strip() for p in paragraphs])
        text_len = len(text)

        # 4️⃣ 链接数量（判断是不是门户）
        links = soup.find_all("a")
        link_count = len(links)

        print("\n=== 页面分析 ===")
        print(f"标题长度: {title_len}")
        print(f"段落数量: {paragraph_count}")
        print(f"正文长度: {text_len}")
        print(f"链接数量: {link_count}")

        # 判定逻辑
        if title_len > 15 and paragraph_count >= 3 and text_len > 300 and link_count < 30:
            return True, "✅ 可用页面"
        else:
            return False, "❌ 垃圾/不适合页面"

    except Exception as e:
        return False, f"异常: {e}"


if __name__ == "__main__":
    url = input("请输入网页URL: ")
    ok, msg = is_good_page(url)
    print(msg)