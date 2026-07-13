import memory_store
import task_manager

def detect_and_save(text):
    text_lower = text.lower()

    keywords = {
        "work": [
            "สมัครงาน",
            "ทำงาน",
            "ส่งพัสดุ",
            "ไปทำงาน"
        ],
        "expense": [
            "บาท",
            "จ่าย",
            "ซื้อ",
            "ค่าใช้จ่าย"
        ],
        "task": [
            "ต้องทำ",
            "นัด",
            "พรุ่งนี้",
            "เตือน"
        ]
    }

    for category in ["task", "work", "expense"]:
        words = keywords[category]
        for word in words:
            if word in text_lower:
                if category == "task":
                    task_manager.add_task(text)

                return memory_store.add_memory(category, text)

    return None
