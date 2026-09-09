"""Persistent, single-source memory manager for Jarvis.

The public API stays compatible with the existing Jarvis runtime:
    save_memory(user, bot)
    get_memory(limit=5) -> list[tuple[str, str]]

Memory is persisted in SQLite so restarting Termux/Jarvis no longer clears
conversation context. The database file is local and ignored by git.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from typing import List, Tuple


PROJECT_ROOT = Path(__file__).resolve().parent
DB_PATH = Path(os.getenv("JARVIS_MEMORY_DB", str(PROJECT_ROOT / "jarvis_memory.db")))

MAX_MEMORY_ROWS = 1000


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.execute("PRAGMA busy_timeout=10000")
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS conversation_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_text TEXT NOT NULL,
            bot_text TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)
    return conn


def save_memory(user, bot):
    """Persist one user/bot exchange."""
    user_text = str(user)
    bot_text = str(bot)

    with _connect() as conn:
        conn.execute(
            "INSERT INTO conversation_memory (user_text, bot_text) VALUES (?, ?)",
            (user_text, bot_text),
        )
        conn.execute(
            """
            DELETE FROM conversation_memory
            WHERE id NOT IN (
                SELECT id FROM conversation_memory ORDER BY id DESC LIMIT ?
            )
            """,
            (MAX_MEMORY_ROWS,),
        )


def get_memory(limit=5) -> List[Tuple[str, str]]:
    """Return the latest exchanges in the same order as the old API."""
    try:
        limit = max(1, min(int(limit), MAX_MEMORY_ROWS))
    except (TypeError, ValueError):
        limit = 5

    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT user_text, bot_text
            FROM conversation_memory
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return list(reversed(rows))


def clear_memory() -> None:
    """Delete all conversational memory."""
    with _connect() as conn:
        conn.execute("DELETE FROM conversation_memory")


def memory_count() -> int:
    """Return the number of persisted conversation exchanges."""
    with _connect() as conn:
        row = conn.execute("SELECT COUNT(*) FROM conversation_memory").fetchone()
    return int(row[0]) if row else 0


def health() -> bool:
    """Return True when the SQLite memory store is readable/writable."""
    try:
        with _connect() as conn:
            conn.execute("SELECT 1").fetchone()
        return True
    except Exception:
        return False
