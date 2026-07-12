import re
import reminder_manager

PLUGIN_NAME = "reminder"


def execute(text=None):
    if not text:
        return "❌ ไม่พบข้อมูล"

    text = text.strip()

    if "ดูรายการเตือน" in text or "ดูเตือน" in text:
        return reminder_manager.list_reminders()

    data = text.replace("ตั้งเตือน", "").strip()

    match = re.search(
        r"(.+?)\s+(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})",
        data
    )

    if not match:
        return "❌ ตัวอย่าง: ตั้งเตือน โทรหาลูกค้า 2026-07-13 09:00"

    task = match.group(1)
    remind_time = match.group(2)

    return reminder_manager.add_reminder(task, remind_time)
