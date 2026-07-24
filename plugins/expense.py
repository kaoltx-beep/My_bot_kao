import re
import expense_manager

PLUGIN_NAME = "expense"

METADATA = {
    "name": "expense",
    "keywords": [
        "จ่าย",
        "ซื้อ",
        "บาท",
        "รายจ่าย",
        "ค่า",
        "กาแฟ",
        "น้ำมัน",
        "อาหาร"
    ]
}


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


def test_case(plugin_name="expense"):
    test_cases = {
        "ไม่มีข้อมูล": "",
        "รายการเงินช่วงเดือนนี้": "ซื้อ 500",
        "ดูรายการ": "ซื้อ 500",
        "รายการน้ำมัน": "น้ำมัน 2000",
        "รายการอาหาร": "อาหาร 700",
        "รายการซื้อ": "ซื้อ 500",
        "รายการไม่พบข้อมูล": "ไม่มี 500",
        "ข้อความที่ไม่เกี่ยวข้อง": "ไม่เกี่ยวข้อง",
        "รายการด้วยจำนวนเงินมากกว่าหมดน้อย": "ซื้อ 1234567890"
    }

    for case, value in test_cases.items():
        result = execute(value)
        if case.startswith("รายการไม่พบข้อมูล"):
            assert result.startswith("❌ ไม่พบข้อมูล")
        elif case.startswith("ข้อความที่ไม่เกี่ยวข้อง"):
            assert result.strip() == "❌ ไม่พบข้อมูล"
        elif case.startswith("รายการด้วยจำนวนเงินมากกว่าหมดน้อย"):
            if amount <= 1000000:
                assert True
            else:
                assert result.startswith("❌ จำนวนเงินนับจากหมดน้อย")
        else:
            assert result.strip() == test_cases[case]

    print("ทั้งหมด 10 รายการ")
