"""models/user.py"""
import secrets
from database.connection import get_conn


def upsert(user_id, username, first_name, last_name=""):
    conn = get_conn()
    ref = secrets.token_hex(4).upper()
    conn.execute("""
        INSERT INTO users(user_id,username,first_name,last_name,ref_code,last_seen)
        VALUES(?,?,?,?,?,datetime('now'))
        ON CONFLICT(user_id) DO UPDATE SET
            username=excluded.username,
            first_name=excluded.first_name,
            last_name=excluded.last_name,
            last_seen=datetime('now')
    """, (user_id, username or "", first_name or "", last_name or "", ref))
    conn.commit()


def get(user_id):
    return get_conn().execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()


def get_all_ids():
    rows = get_conn().execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()
    return [r["user_id"] for r in rows]


def ban(user_id, flag=1):
    conn = get_conn()
    conn.execute("UPDATE users SET is_banned=? WHERE user_id=?", (flag, user_id))
    conn.commit()


def add_spent(user_id, amount):
    conn = get_conn()
    conn.execute("UPDATE users SET total_spent=total_spent+? WHERE user_id=?", (amount, user_id))
    conn.commit()


def count():
    return get_conn().execute("SELECT COUNT(*) FROM users").fetchone()[0]
