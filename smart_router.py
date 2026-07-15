def detect_type(text):
    text = text.lower()

    if any(x in text for x in ["ติดตั้ง", "ไฟเบอร์", "fiber", "3bb", "true", "ais"]):
        return "work"

    if any(x in text for x in ["บาท", "ซื้อ", "จ่าย", "ค่า", "เงิน"]):
        return "expense"

    if any(x in text for x in ["เพิ่มงาน", "ต้องทำ", "เตือน"]):
        return "task"

    if any(x in text for x in ["จำไว้", "จำว่า", "จำ"]):
        return "memory"

    return "chat"
