"""models/payment.py"""
from database.connection import get_conn


def save(order_id, user_id, method, screenshot_id, trx_ref=None):
    conn = get_conn()
    conn.execute("""
        INSERT OR REPLACE INTO payments
          (order_id,user_id,method,screenshot_id,trx_ref)
        VALUES(?,?,?,?,?)
    """, (order_id, user_id, method, screenshot_id, trx_ref))
    conn.commit()


def get_by_order(order_id):
    return get_conn().execute(
        "SELECT * FROM payments WHERE order_id=?", (order_id,)
    ).fetchone()


def verify(order_id):
    conn = get_conn()
    conn.execute("""
        UPDATE payments
        SET status='verified', verified_at=datetime('now')
        WHERE order_id=?
    """, (order_id,))
    conn.commit()
