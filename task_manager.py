import sqlite3
from datetime import datetime

DB = "task.db"

def init():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task TEXT,
        date TEXT,
        status TEXT
    )
    """)
    conn.commit()
    conn.close()

def add_task(task):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "INSERT INTO tasks (task,date,status) VALUES (?,?,?)",
        (task, datetime.now().strftime("%Y-%m-%d %H:%M"), "pending")
    )
    conn.commit()
    conn.close()
    return f"📝 บันทึกงาน: {task} แล้ว"

def list_tasks():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT task,date,status FROM tasks ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()

    if not rows:
        return "📋 ยังไม่มีงาน"

    result = "📋 รายการงาน\n"
    for task,date,status in rows:
        result += f"{date} | {task} | {status}\n"

    return result

init()
