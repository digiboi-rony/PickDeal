"""models/order.py"""
from database.connection import get_conn

STATUS_EMOJI = {
    "pending":           "🕐",
    "payment_confirmed": "✅",
    "processing":        "⚙️",
    "packed":            "📦",
    "shipping":          "🚚",
    "out_for_delivery":  "🛵",
    "delivered":         "🎉",
    "cancelled":         "❌",
}

STATUS_LABEL = {
    "pending":           "অপেক্ষমান",
    "payment_confirmed": "পেমেন্ট নিশ্চিত",
    "processing":        "প্রসেসিং",
    "packed":            "প্যাক হয়েছে",
    "shipping":          "শিপিং চলছে",
    "out_for_delivery":  "ডেলিভারিতে আছে",
    "delivered":         "ডেলিভারি হয়েছে",
    "cancelled":         "বাতিল",
}

# Next valid statuses for each status
STATUS_FLOW = {
    "pending":           ["payment_confirmed", "cancelled"],
    "payment_confirmed": ["processing", "cancelled"],
    "processing":        ["packed"],
    "packed":            ["shipping"],
    "shipping":          ["out_for_delivery"],
    "out_for_delivery":  ["delivered"],
    "delivered":         [],
    "cancelled":         [],
}


def create(user_id, full_name, phone, address, area, notes,
           subtotal, delivery_fee, discount, total,
           coupon_code, payment_method):
    conn = get_conn()
    c = conn.execute("""
        INSERT INTO orders
          (user_id,full_name,phone,address,area,notes,
           subtotal,delivery_fee,discount,total,coupon_code,payment_method)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
    """, (user_id, full_name, phone, address, area, notes,
          subtotal, delivery_fee, discount, total, coupon_code, payment_method))
    conn.commit()
    return c.lastrowid


def add_items(order_id, items: list[dict]):
    conn = get_conn()
    for it in items:
        conn.execute("""
            INSERT INTO order_items
              (order_id,product_id,product_name,quantity,unit_price,total_price)
            VALUES(?,?,?,?,?,?)
        """, (order_id, it["product_id"], it["product_name"],
              it["quantity"], it["unit_price"], it["quantity"] * it["unit_price"]))
    conn.commit()


def get(order_id):
    return get_conn().execute("""
        SELECT o.*, u.first_name, u.username
        FROM orders o JOIN users u ON o.user_id=u.user_id
        WHERE o.order_id=?
    """, (order_id,)).fetchone()


def get_items(order_id):
    return get_conn().execute(
        "SELECT * FROM order_items WHERE order_id=?", (order_id,)
    ).fetchall()


def get_user_orders(user_id, limit=10):
    return get_conn().execute("""
        SELECT * FROM orders WHERE user_id=?
        ORDER BY created_at DESC LIMIT ?
    """, (user_id, limit)).fetchall()


def get_all(status=None, page=0, per_page=8):
    offset = page * per_page
    if status and status != "all":
        return get_conn().execute("""
            SELECT o.*, u.first_name FROM orders o
            JOIN users u ON o.user_id=u.user_id
            WHERE o.status=?
            ORDER BY o.created_at DESC LIMIT ? OFFSET ?
        """, (status, per_page, offset)).fetchall()
    return get_conn().execute("""
        SELECT o.*, u.first_name FROM orders o
        JOIN users u ON o.user_id=u.user_id
        ORDER BY o.created_at DESC LIMIT ? OFFSET ?
    """, (per_page, offset)).fetchall()


def update_status(order_id, status):
    conn = get_conn()
    conn.execute(
        "UPDATE orders SET status=?, updated_at=datetime('now') WHERE order_id=?",
        (status, order_id)
    )
    conn.commit()


def stats():
    conn = get_conn()
    total   = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
    revenue = conn.execute(
        "SELECT COALESCE(SUM(total),0) FROM orders WHERE status='delivered'"
    ).fetchone()[0]
    today   = conn.execute(
        "SELECT COUNT(*) FROM orders WHERE DATE(created_at)=DATE('now')"
    ).fetchone()[0]
    by_st   = conn.execute(
        "SELECT status, COUNT(*) as n FROM orders GROUP BY status"
    ).fetchall()
    return {
        "total":     total,
        "revenue":   revenue,
        "today":     today,
        "by_status": {r["status"]: r["n"] for r in by_st},
    }
