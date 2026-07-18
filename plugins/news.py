import requests
import json
from groq import Groq
import os

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


def execute(text=None):
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

            # แปลข่าวเป็นภาษาไทยโดยใช้ Groq API
            try:
                groq_key = os.getenv("GROQ_API_KEY", "")
                if groq_key:
                    client = Groq(api_key=groq_key)
                    translation = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[
                            {"role": "system", "content": "คุณเป็นนักแปลภาษาอังกฤษเป็นไทย แปลให้สั้นกระชับ"},
                            {"role": "user", "content": f"แปลเป็นไทย:\n{title}"}
                        ],
                        max_tokens=100
                    )
                    thai_title = translation.choices[0].message.content.strip()
                else:
                    thai_title = title
            except:
                thai_title = title

            result += f"""
ข่าวที่ {i}
หัวข้อ: {thai_title}

รายละเอียด:
{summary[:200]}

"""

        return result

    except Exception as e:
        return f"ดึงข่าวไม่สำเร็จครับ {e}"
