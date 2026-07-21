def handle_developer_request(text):
    text = text.lower()

    keywords = [
        "เพิ่มฟังก์ชั่น",
        "แก้โค้ด",
        "ocr",
        "เขียนโค้ด",
        "พัฒนาตัวเอง"
    ]

    for key in keywords:
        if key in text:
            return {
                "mode": "developer",
                "status": "request_received",
                "message": "รับคำขอแล้ว กำลังวิเคราะห์ระบบ"
            }

    return None
