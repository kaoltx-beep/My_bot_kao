PLUGIN_NAME = "checklist"

METADATA = {
    "name": "checklist",
    "keywords": [
        "เช็คลิสต์อบรม",
        "ดูอุปกรณ์อบรม",
        "เหลืออะไรบ้าง",
        "ติ๊ก",
        "ยกเลิก",
        "อุปกรณ์อบรม",
        "checklist"
    ]
}


def execute(text=None):
    if not text:
        return "📋 เช็คลิสต์อบรม"

    if "เช็คลิสต์อบรม" in text or "ดูอุปกรณ์อบรม" in text:
        return """📋 เช็คลิสต์อบรม

⬜ เสื้อผ้าใส่อบรม
⬜ รองเท้า
⬜ ปากกา / สมุดจด
⬜ โทรศัพท์ + สายชาร์จ

บริษัทเตรียมให้:
⬜ คู่มืออบรม
⬜ อุปกรณ์ฝึก"""

    if "เหลืออะไรบ้าง" in text:
        return "⬜ ยังเหลือรายการเตรียมอบรม"

    if text.startswith("ติ๊ก"):
        return "✅ ติ๊กเรียบร้อย"

    if text.startswith("ยกเลิก"):
        return "↩️ ยกเลิกเรียบร้อย"

    return "📋 เช็คลิสต์อบรม"


def run_checklist(checklist, item):
    if item in checklist:
        return "✅ ติ๊กเรียบร้อย"
    else:
        return "❌ อุปกรณ์นี้ยังเหลือ"
