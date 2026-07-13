import sqlite3
from datetime import datetime

DB = "reminder.db"


def init():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        text TEXT,
        remind_time TEXT,
        status TEXT
    )
    """)

    conn.commit()
    conn.close()


def add_reminder(text, remind_time):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute(
        "INSERT INTO reminders (text, remind_time, status) VALUES (?, ?, ?)",
        (text, remind_time, "waiting")
    )

    conn.commit()
    conn.close()

    return f"⏰ ตั้งเตือน: {text} เวลา {remind_time} แล้ว"


def list_reminders():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute(
        "SELECT text, remind_time, status FROM reminders ORDER BY id DESC"
    )

    rows = c.fetchall()
    conn.close()

    if not rows:
        return "⏰ ยังไม่มีรายการเตือน"

    result = "⏰ รายการเตือน\n"

    for text, time, status in rows:
        result += f"{time} | {text} | {status}\n"

    return result


init()


def delete_reminder(reminder_id):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("DELETE FROM reminders WHERE id=?", (reminder_id,))
    deleted = c.rowcount

    conn.commit()
    conn.close()

    if deleted:
        return f"🗑️ ลบรายการเตือน #{reminder_id} แล้ว"

    return "❌ ไม่พบรายการเตือน"
