import re
import expense_manager

PLUGIN_NAME = "expense"


def execute(text=None):
    if not text:
        return "❌ ไม่พบข้อมูล"

    text = text.lower()

    if "เดือนนี้" in text or "รายเดือน" in text:
        return expense_manager.monthly_summary()

    if "ดูรายจ่าย" in text or "รายการ" in text:
        return expense_manager.list_expenses()

    match = re.search(r"(.+?)\s+(\d+)", text)

    if not match:
        return "❌ ตัวอย่าง: น้ำมัน 500"

    item = match.group(1)
    amount = float(match.group(2))

    return expense_manager.add_expense(item, amount)
