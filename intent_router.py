def classify(text):
    text = text.lower()

    if any(x in text for x in ["ติดตั้ง", "ไฟเบอร์", "fiber", "3bb", "true", "ais"]):
        return "work"

    if any(x in text for x in ["บาท", "ซื้อ", "จ่าย", "ค่า", "เงิน"]):
        return "add_expense"

    if any(x in text for x in ["แบต", "battery", "แบตเตอรี่"]):
        return "check_battery"

    if any(x in text for x in ["youtube", "ยูทูป", "เปิดเพลง"]):
        return "open_youtube"

    return None
