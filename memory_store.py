import sqlite3
from datetime import datetime

DB = "jarvis_memory.db"


def init():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS memories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT,
        content TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


def detect_category(text):
    text = text.lower()

    if any(x in text for x in ["jarvis", "โค้ด", "โปรเจกต์", "ระบบ"]):
        return "project"

    if any(x in text for x in ["งาน", "สมัคร", "ส่งพัสดุ", "ทำงาน"]):
        return "work"

    if any(x in text for x in ["ต้องทำ", "ทำวัน", "เตือน"]):
        return "task"

    if any(x in text for x in ["คิดว่า", "ไอเดีย", "อยากทำ"]):
        return "idea"

    if any(x in text for x in ["บาท", "จ่าย", "เงิน", "ค่าใช้จ่าย"]):
        return "expense"

    return "general"


def add_memory(category, content=None):
    if content is None:
        content = category
        category = detect_category(content)

    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute(
        "SELECT id FROM memories WHERE category=? AND content=?",
        (category, content)
    )

    if c.fetchone():
        conn.close()
        return f"🧠 มีความจำนี้อยู่แล้ว [{category}]: {content}"

    c.execute(
        "INSERT INTO memories (category, content, created_at) VALUES (?, ?, ?)",
        (
            category,
            content,
            datetime.now().strftime("%Y-%m-%d %H:%M")
        )
    )

    conn.commit()
    conn.close()

    return f"🧠 จำไว้แล้ว [{category}]: {content}"


def search_memory(keyword):
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute(
        "SELECT category, content, created_at FROM memories WHERE content LIKE ?",
        (f"%{keyword}%",)
    )

    rows = c.fetchall()
    conn.close()

    if not rows:
        return "ไม่พบข้อมูล"

    result = "🧠 ความจำที่พบ\n"

    for category, content, date in rows:
        result += f"[{category}] {content} ({date})\n"

    return result


def summary_memory():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("""
    SELECT category, content
    FROM memories
    ORDER BY id DESC
    """)

    rows = c.fetchall()
    conn.close()

    if not rows:
        return "🧠 ยังไม่มีความจำ"

    result = "🧠 สรุปความจำ\n"

    current = None

    for category, content in rows:
        if category != current:
            current = category
            result += f"\n[{category}]\n"

        result += f"- {content}\n"

    return result
