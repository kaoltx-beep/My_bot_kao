import sqlite3
import time
from pathlib import Path

from memory_google import save_memory as save_google_memory

DB_PATH = Path("jarvis_memory.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user TEXT,
        bot TEXT,
        created_at INTEGER
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS facts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key TEXT UNIQUE,
        value TEXT,
        created_at INTEGER
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_profile (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    conn.commit()
    conn.close()


init_db()


def save_memory(user, bot):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO conversations(user, bot, created_at) VALUES (?, ?, ?)",
        (user, bot, int(time.time()))
    )

    conn.commit()
    conn.close()

    try:
        save_google_memory(
            user,
            bot
        )
    except Exception as e:
        print("Google Memory Backup Error:", e)


def get_memory(limit=5):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        "SELECT user, bot FROM conversations ORDER BY id DESC LIMIT ?",
        (limit,)
    )

    rows = cur.fetchall()
    conn.close()

    return list(reversed(rows))


def save_fact(key, value):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        "INSERT OR REPLACE INTO facts(key, value, created_at) VALUES (?, ?, ?)",
        (key, value, int(time.time()))
    )

    conn.commit()
    conn.close()


def get_fact(key):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        "SELECT value FROM facts WHERE key=?",
        (key,)
    )

    result = cur.fetchone()
    conn.close()

    return result[0] if result else None


def set_profile(key, value):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        "INSERT OR REPLACE INTO user_profile(key,value) VALUES (?,?)",
        (key, value)
    )

    conn.commit()
    conn.close()


def get_profile(key):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute(
        "SELECT value FROM user_profile WHERE key=?",
        (key,)
    )

    result = cur.fetchone()
    conn.close()

    return result[0] if result else None