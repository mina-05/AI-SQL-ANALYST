"""App-level storage: user accounts and query history (also used as chat memory)."""
import sqlite3
from contextlib import closing
from pathlib import Path

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    conversation_id TEXT NOT NULL,
    mode TEXT NOT NULL DEFAULT 'quick',
    question TEXT NOT NULL,
    sql TEXT,
    row_count INTEGER,
    answer TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_history_user ON history(user_id, id);
CREATE INDEX IF NOT EXISTS idx_history_conv ON history(user_id, conversation_id, id);
"""


def _connect():
    path = Path(config.APP_DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def create_user(username: str, password_hash: str) -> int:
    with closing(_connect()) as conn, conn:
        try:
            cur = conn.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password_hash)
            )
        except sqlite3.IntegrityError:
            raise ValueError("That username is already taken.")
        return cur.lastrowid


def get_user_by_name(username: str):
    with closing(_connect()) as conn:
        row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        return dict(row) if row else None


def get_user(user_id: int):
    with closing(_connect()) as conn:
        row = conn.execute("SELECT id, username FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def add_history(user_id, conversation_id, mode, question, sql, row_count, answer):
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT INTO history (user_id, conversation_id, mode, question, sql, row_count, answer) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (user_id, conversation_id, mode, question, sql, row_count, answer),
        )


def recent_turns(user_id: int, conversation_id: str, limit: int) -> list:
    """Last `limit` turns of one conversation, oldest first (this is the chat memory)."""
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT question, sql, answer FROM history WHERE user_id = ? AND conversation_id = ? "
            "ORDER BY id DESC LIMIT ?",
            (user_id, conversation_id, limit),
        ).fetchall()
    return [dict(r) for r in reversed(rows)]


def list_history(user_id: int, limit: int = 50) -> list:
    with closing(_connect()) as conn:
        rows = conn.execute(
            "SELECT id, conversation_id, mode, question, sql, row_count, created_at "
            "FROM history WHERE user_id = ? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
    return [dict(r) for r in rows]


def clear_history(user_id: int) -> None:
    with closing(_connect()) as conn, conn:
        conn.execute("DELETE FROM history WHERE user_id = ?", (user_id,))
