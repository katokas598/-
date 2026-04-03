import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "bot.db")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            channel_id TEXT,
            category TEXT,
            status TEXT DEFAULT 'open',
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS ticket_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id INTEGER,
            action TEXT,
            user_id TEXT,
            message TEXT,
            timestamp TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS warns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            reason TEXT,
            moderator_id TEXT,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mutes (
            user_id TEXT PRIMARY KEY,
            end_time TEXT,
            reason TEXT,
            moderator_id TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mod_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            action TEXT,
            user_id TEXT,
            moderator_id TEXT,
            reason TEXT,
            timestamp TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_commands (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trigger TEXT UNIQUE NOT NULL,
            response TEXT NOT NULL,
            created_by TEXT,
            created_at TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS welcome_config (
            id INTEGER PRIMARY KEY,
            channel_id TEXT,
            message TEXT,
            enabled INTEGER DEFAULT 0
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS web_users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL,
            session_token TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()


def get_setting(key, default=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    result = cursor.fetchone()
    conn.close()
    if result:
        try:
            return json.loads(result[0])
        except:
            return result[0]
    return default


def set_setting(key, value):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    value_json = json.dumps(value) if isinstance(value, (list, dict)) else str(value)
    cursor.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value_json)
    )
    conn.commit()
    conn.close()


def create_ticket(user_id, channel_id, category):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    created_at = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO tickets (user_id, channel_id, category, status, created_at) VALUES (?, ?, ?, ?, ?)",
        (user_id, channel_id, category, "open", created_at),
    )
    ticket_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return ticket_id


def close_ticket(channel_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE tickets SET status = ? WHERE channel_id = ?", ("closed", channel_id)
    )
    conn.commit()
    conn.close()


def get_ticket_by_channel(channel_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets WHERE channel_id = ?", (str(channel_id),))
    result = cursor.fetchone()
    conn.close()
    return result


def add_ticket_log(ticket_id, action, user_id, message=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO ticket_logs (ticket_id, action, user_id, message, timestamp) VALUES (?, ?, ?, ?, ?)",
        (ticket_id, action, user_id, message, timestamp),
    )
    conn.commit()
    conn.close()


def add_warn(user_id, reason, moderator_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    created_at = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO warns (user_id, reason, moderator_id, created_at) VALUES (?, ?, ?, ?)",
        (user_id, reason, moderator_id, created_at),
    )
    conn.commit()
    conn.close()


def get_warns(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM warns WHERE user_id = ?", (user_id,))
    result = cursor.fetchall()
    conn.close()
    return result


def get_warns_count(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM warns WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()[0]
    conn.close()
    return result


def clear_warns(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM warns WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def add_mute(user_id, end_time, reason, moderator_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO mutes (user_id, end_time, reason, moderator_id) VALUES (?, ?, ?, ?)",
        (user_id, end_time, reason, moderator_id),
    )
    conn.commit()
    conn.close()


def remove_mute(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM mutes WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()


def get_mute(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM mutes WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result


def add_mod_log(action, user_id, moderator_id, reason=""):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO mod_logs (action, user_id, moderator_id, reason, timestamp) VALUES (?, ?, ?, ?, ?)",
        (action, user_id, moderator_id, reason, timestamp),
    )
    conn.commit()
    conn.close()


def get_mod_logs(limit=50):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM mod_logs ORDER BY id DESC LIMIT ?", (limit,))
    result = cursor.fetchall()
    conn.close()
    return result


# Custom Commands
def add_custom_command(trigger, response, created_by=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    created_at = datetime.now().isoformat()
    cursor.execute(
        "INSERT INTO custom_commands (trigger, response, created_by, created_at) VALUES (?, ?, ?, ?)",
        (trigger, response, created_by, created_at),
    )
    conn.commit()
    conn.close()


def get_custom_commands():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM custom_commands ORDER BY id DESC")
    result = cursor.fetchall()
    conn.close()
    return result


def get_custom_command(trigger):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM custom_commands WHERE trigger = ?", (trigger,))
    result = cursor.fetchone()
    conn.close()
    return result


def delete_custom_command(trigger):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM custom_commands WHERE trigger = ?", (trigger,))
    conn.commit()
    conn.close()


# Welcome Config
def get_welcome_config():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM welcome_config WHERE id = 1")
    result = cursor.fetchone()
    conn.close()
    return result


def set_welcome_config(channel_id, message, enabled=1):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR REPLACE INTO welcome_config (id, channel_id, message, enabled) VALUES (1, ?, ?, ?)",
        (channel_id, message, enabled),
    )
    conn.commit()
    conn.close()


# Web Users
def add_web_user(username, password_hash):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    created_at = datetime.now().isoformat()
    cursor.execute(
        "INSERT OR REPLACE INTO web_users (username, password_hash, created_at) VALUES (?, ?, ?)",
        (username, password_hash, created_at),
    )
    conn.commit()
    conn.close()


def get_web_user(username):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM web_users WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    return result


def get_all_tickets():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets ORDER BY id DESC")
    result = cursor.fetchall()
    conn.close()
    return result


def get_open_tickets():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tickets WHERE status = 'open' ORDER BY id DESC")
    result = cursor.fetchall()
    conn.close()
    return result
