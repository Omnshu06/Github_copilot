# database.py
import sqlite3

DB_NAME = "codeassistant.db"


def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                name TEXT,
                password TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT,
                query TEXT,
                response TEXT,
                lang TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_email) REFERENCES users(email)
            )
        """)
        conn.commit()


def add_user(name: str, email: str, password: str):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute(
                "INSERT INTO users (email, name, password) VALUES (?, ?, ?)",
                (email, name, password)
            )
            conn.commit()
        return True
    except Exception:
        return False


def verify_user(email: str, password: str):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT name, email FROM users WHERE email=? AND password=?",
            (email, password)
        )
        return cur.fetchone()


def save_chat(user_email: str, query: str, response: str, lang: str):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute(
            "INSERT INTO chats (user_email, query, response, lang) VALUES (?, ?, ?, ?)",
            (user_email, query, response, lang)
        )
        conn.commit()


def get_chat_history(user_email: str, limit: int = 20):
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT query, response, lang, timestamp FROM chats
            WHERE user_email = ?
            ORDER BY timestamp DESC LIMIT ?
        """, (user_email, limit))
        rows = cur.fetchall()
        return [
            {"query": r[0], "response": r[1], "lang": r[2], "time": r[3]}
            for r in rows
        ]