import sqlite3
import json
from datetime import datetime, timezone

DB_PATH = "chat.db"


def _connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            key_combo TEXT NOT NULL DEFAULT '{}',
            fernet_key BLOB NOT NULL
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT NOT NULL,
            recipient TEXT NOT NULL,
            ciphertext TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'PENDING',
            timestamp TEXT NOT NULL,
            FOREIGN KEY (sender) REFERENCES users(username),
            FOREIGN KEY (recipient) REFERENCES users(username)
        );
    """)
    conn.close()


def get_user(username):
    conn = _connect()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def create_user(username, password_hash, key_combo, fernet_key):
    conn = _connect()
    conn.execute(
        "INSERT OR IGNORE INTO users (username, password_hash, key_combo, fernet_key) VALUES (?, ?, ?, ?)",
        (username, password_hash, json.dumps(key_combo), fernet_key),
    )
    conn.commit()
    conn.close()


def update_password(username, new_hash):
    conn = _connect()
    conn.execute("UPDATE users SET password_hash = ? WHERE username = ?", (new_hash, username))
    conn.commit()
    conn.close()


def update_key_combo(username, key_combo):
    conn = _connect()
    conn.execute("UPDATE users SET key_combo = ? WHERE username = ?", (json.dumps(key_combo), username))
    conn.commit()
    conn.close()


def create_message(sender, recipient, ciphertext):
    conn = _connect()
    ts = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO messages (sender, recipient, ciphertext, status, timestamp) VALUES (?, ?, ?, 'PENDING', ?)",
        (sender, recipient, ciphertext, ts),
    )
    conn.commit()
    conn.close()


def get_messages():
    conn = _connect()
    rows = conn.execute("SELECT * FROM messages ORDER BY timestamp ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_message_status(msg_id, status):
    conn = _connect()
    conn.execute("UPDATE messages SET status = ? WHERE id = ?", (status, msg_id))
    conn.commit()
    conn.close()


def clear_chat():
    conn = _connect()
    conn.execute("DELETE FROM messages")
    conn.commit()
    conn.close()
