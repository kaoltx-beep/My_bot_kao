import re

def extract_work(text):
    data = {
        "customer": "ไม่ระบุ",
        "provider": "ไม่ระบุ",
        "address": "ไม่ระบุ",
        "status": "รับเรื่อง",
        "note": text
    }

    # ลูกค้า
    m = re.search(r"(?:ลูกค้า|ให้กับ)\s*([^\s]+)", text)
    if m:
        data["customer"] = m.group(1)

    # ผู้ให้บริการ
    for p in ["3BB", "True", "AIS", "NT"]:
        if p.lower() in text.lower():
            data["provider"] = p
            break

    # สถานที่
    m = re.search(r"(?:ที่อยู่|จังหวัด|อำเภอ|ที่)\s*([^\s]+)", text)
    if m:
        data["address"] = m.group(1)

    # สถานะ
    if "เสร็จ" in text or "เรียบร้อย" in text or "เสร็จแล้ว" in text:
        data["status"] = "เสร็จ"

    return data
