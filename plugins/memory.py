import re
import memory_store

PLUGIN_NAME = "memory"

METADATA = {
    "keywords": [
        "จำไว้",
        "จำว่า",
        "ค้นหา",
        "จำอะไร",
        "สรุปความจำ"
    ]
}

def clean_memory_text(text):
    text = text.strip()

    prefixes = [
        "จำไว้ว่าฉัน",
        "จำไว้ว่า",
        "จำไว้",
        "จำว่า",
        "ว่า"
    ]

    for p in prefixes:
        if text.startswith(p):
            text = text[len(p):]
            if p == "จำไว้ว่าฉัน":
                text = "ฉัน" + text
            break

    return text.strip()


def execute(text=None):
    if not text:
        return "❌ ไม่พบข้อมูล"

    text = text.strip()

    if "สรุปความจำ" in text:
        return memory_store.summary_memory()

    if "จำไว้" in text or "จำว่า" in text:
        content = clean_memory_text(text)

        if not content:
            return "❌ ตัวอย่าง: จำไว้ว่าฉันกำลังสมัครงาน"

        return memory_store.add_memory(content)

    if "ค้นหา" in text or "จำอะไร" in text:
        keyword = re.sub(r"ค้นหา|จำอะไร", "", text).strip()
        return memory_store.search_memory(keyword)

    return "❌ ไม่เข้าใจคำสั่งความจำ"
