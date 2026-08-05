import sqlite3

DB_NAME = "jarvis_memory.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_text TEXT,
            bot_text TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_memory(user_text, bot_text):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "INSERT INTO memory (user_text, bot_text) VALUES (?, ?)",
        (user_text, bot_text)
    )
    conn.commit()
    conn.close()

def get_memory(limit=5):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute(
        "SELECT user_text, bot_text FROM memory ORDER BY id DESC LIMIT ?",
        (limit,)
    )
    rows = c.fetchall()
    conn.close()
    return rows