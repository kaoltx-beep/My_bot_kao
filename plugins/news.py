import requests

METADATA = {
    "name": "news",
    "description": "อ่านข่าวล่าสุด",
    "keywords": [
        "ข่าว",
        "ข่าววันนี้",
        "ข่าวล่าสุด",
        "อ่านข่าว"
    ]
}


def execute():
    try:
        url = "https://api.spaceflightnewsapi.net/v4/articles/?limit=5"

        r = requests.get(url, timeout=10)
        data = r.json()

        articles = data.get("results", [])

        if not articles:
            return "ไม่มีข่าวใหม่ครับ"

        result = "ข่าวล่าสุด:\n\n"

        for i, item in enumerate(articles[:5], 1):
            title = item.get("title", "")
            summary = item.get("summary", "")

            result += f"""
ข่าวที่ {i}
หัวข้อ: {title}

รายละเอียด:
{summary[:200]}

"""

        return result

    except Exception as e:
        return f"ดึงข่าวไม่สำเร็จครับ {e}"
