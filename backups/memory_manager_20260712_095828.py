import sqlite3

DB_NAME = "memory.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS memory(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT NOT NULL,
        bot TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


def save_memory(user, bot):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO memory(user, bot) VALUES(?, ?)",
        (user, bot)
    )

    conn.commit()
    conn.close()


def get_memory(limit=5):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute(
        "SELECT user, bot FROM memory ORDER BY id DESC LIMIT ?",
        (limit,)
    )

    rows = cur.fetchall()
    conn.close()

    rows.reverse()
    return rows


def clear_memory():
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()

    cur.execute("DELETE FROM memory")

    conn.commit()
    conn.close()


init_db()
