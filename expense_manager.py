import sqlite3
from datetime import datetime

DB = "expense.db"

def init():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item TEXT,
        amount REAL,
        date TEXT
    )
    """)
    conn.commit()
    conn.close()

def add_expense(item, amount):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute(
        "INSERT INTO expenses (item, amount, date) VALUES (?, ?, ?)",
        (item, amount, datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    conn.commit()
    conn.close()
    return f"บันทึก {item} {amount} บาทแล้ว"

def summary():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT SUM(amount) FROM expenses")
    total = c.fetchone()[0] or 0
    conn.close()
    return f"ค่าใช้จ่ายรวม {total} บาท"

init()

def list_expenses():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    c.execute("SELECT item, amount, date FROM expenses ORDER BY id DESC")

    rows = c.fetchall()
    conn.close()

    if not rows:
        return "ยังไม่มีรายการ"

    result = "📋 รายการค่าใช้จ่าย\n"

    for item, amount, date in rows:
        result += f"{date} | {item} | {amount} บาท\n"

    return result

def monthly_summary():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    month = datetime.now().strftime("%Y-%m")

    c.execute(
        "SELECT SUM(amount) FROM expenses WHERE date LIKE ?",
        (month + "%",)
    )

    total = c.fetchone()[0] or 0
    conn.close()

    return f"📊 ค่าใช้จ่ายเดือนนี้รวม {total} บาท"
