"""Jarvis Developer Mode router helper"""

from dev_handler import handle_dev_request


def is_developer_command(text):
    keywords = [
        "วิเคราะห์โปรเจกต์",
        "ตรวจ error",
        "ช่วยแก้โค้ด",
        "วิเคราะห์โค้ด",
        "สร้าง patch",
    ]
    return any(k in text for k in keywords)


def execute_developer_command(text, root="."):
    return handle_dev_request(text, root)
