"""
Jarvis Developer Session
เก็บงานที่รอการยืนยันก่อนแก้ไฟล์
"""

pending = {}


def create(chat_id, filename, old_code, new_code):
    pending[chat_id] = {
        "file": filename,
        "old": old_code,
        "new": new_code
    }


def get(chat_id):
    return pending.get(chat_id)


def clear(chat_id):
    if chat_id in pending:
        del pending[chat_id]
