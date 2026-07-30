"""Jarvis Developer Mode router."""

from dev_handler import handle_dev_request
import developer_mode


_PROJECT_COMMANDS = ("วิเคราะห์โปรเจกต์", "ตรวจโปรเจกต์", "scan โปรเจกต์")
_DEV_KEYWORDS = (
    "วิเคราะห์โปรเจกต์",
    "ตรวจโปรเจกต์",
    "ตรวจ error",
    "ช่วยแก้โค้ด",
    "วิเคราะห์โค้ด",
    "สร้าง patch",
    "แก้โค้ด",
    "แก้ไฟล์",
)


def is_developer_command(text: str) -> bool:
    normalized = (text or "").lower()
    return any(k in normalized for k in _DEV_KEYWORDS)


def execute_developer_command(text: str, root=".", groq_client=None):
    normalized = (text or "").lower()
    if any(k in normalized for k in _PROJECT_COMMANDS):
        return handle_dev_request(text, root)
    return developer_mode.handle(text, groq_client=groq_client)
