"""
database/queries.py
===================
All database query functions in one place.
Import and use these throughout the bot — never write raw SQL elsewhere.
"""

import logging
from database.db_setup import get_connection

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# USER QUERIES
# ═══════════════════════════════════════════════════════════════════

def upsert_user(user_id: int, username: str, first_name: str, last_name: str):
    """Create or update a user record when they interact with the bot."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO users (user_id, username, first_name, last_name)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            username   = excluded.username,
            first_name = excluded.first_name,
            last_name  = excluded.last_name
    """, (user_id, username, first_name, last_name))
    conn.commit()
    conn.close()


def get_user(user_id: int):
    """Fetch a single user by their Telegram user_id."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row


def get_all_users():
    """Get all users (used for broadcast messages)."""
    conn = get_connection()
    rows = conn.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    return [r["user_id"] for r in rows]


# ═══════════════════════════════════════════════════════════════════
# PRODUCT QUERIES
# ═══════════════════════════════════════════════════════════════════

def get_categories():
    """Get all unique product categories that have active products."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT DISTINCT category FROM products WHERE is_active = 1 ORDER BY category"
    ).fetchall()
    conn.close()
    return [r["category"] for r in rows]


def get_products_by_category(category: str):
    """Get all active products in a specific category."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM products WHERE category = ? AND is_active = 1 ORDER BY name",
        (category,)
    ).fetchall()
    conn.close()
    return rows


def get_product(product_id: int):
    """Get a single product by its ID."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM products WHERE product_id = ?", (product_id,)
    ).fetchone()
    conn.close()
    return row


def search_products(query: str):
    """Search products by name or description (case-insensitive)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM products WHERE is_active = 1 AND (name LIKE ? OR description LIKE ?)",
        (f"%{query}%", f"%{query}%")
    ).fetchall()
    conn.close()
    return rows


def update_product_stock(product_id: int, quantity_sold: int):
    """Reduce stock when an order is confirmed."""
    conn = get_connection()
    conn.execute(
        "UPDATE products SET stock = stock - ? WHERE product_id = ?",
        (quantity_sold, product_id)
    )
    conn.commit()
    conn.close()


# ═══════════════════════════════════════════════════════════════════
# ORDER QUERIES
# ═══════════════════════════════════════════════════════════════════

def create_order(user_id, product_id, quantity, total_price, full_name, phone, address,
                 coupon_code=None, discount=0):
    """Insert a new order and return the generated order_id."""
    conn = get_connection()
    cursor = conn.execute("""
        INSERT INTO orders
            (user_id, product_id, quantity, total_price, full_name, phone, address, coupon_code, discount)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, product_id, quantity, total_price, full_name, phone, address, coupon_code, discount))
    order_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return order_id


def get_order(order_id: int):
    """Get a single order with product name joined."""
    conn = get_connection()
    row = conn.execute("""
        SELECT o.*, p.name AS product_name, p.category
        FROM orders o
        JOIN products p ON o.product_id = p.product_id
        WHERE o.order_id = ?
    """, (order_id,)).fetchone()
    conn.close()
    return row


def get_user_orders(user_id: int):
    """Get all orders for a specific user, newest first."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT o.*, p.name AS product_name
        FROM orders o
        JOIN products p ON o.product_id = p.product_id
        WHERE o.user_id = ?
        ORDER BY o.created_at DESC
        LIMIT 10
    """, (user_id,)).fetchall()
    conn.close()
    return rows


def get_all_orders(status_filter=None, limit=20, offset=0):
    """Get all orders for admin view, optionally filtered by status."""
    conn = get_connection()
    if status_filter and status_filter != "all":
        rows = conn.execute("""
            SELECT o.*, p.name AS product_name, u.first_name
            FROM orders o
            JOIN products p ON o.product_id = p.product_id
            JOIN users u ON o.user_id = u.user_id
            WHERE o.status = ?
            ORDER BY o.created_at DESC
            LIMIT ? OFFSET ?
        """, (status_filter, limit, offset)).fetchall()
    else:
        rows = conn.execute("""
            SELECT o.*, p.name AS product_name, u.first_name
            FROM orders o
            JOIN products p ON o.product_id = p.product_id
            JOIN users u ON o.user_id = u.user_id
            ORDER BY o.created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset)).fetchall()
    conn.close()
    return rows


def update_order_status(order_id: int, new_status: str):
    """Update the delivery status of an order."""
    conn = get_connection()
    conn.execute("""
        UPDATE orders
        SET status = ?, updated_at = datetime('now')
        WHERE order_id = ?
    """, (new_status, order_id))
    conn.commit()
    conn.close()


def count_orders_by_status():
    """Get count of orders grouped by status (for admin dashboard)."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT status, COUNT(*) as cnt FROM orders GROUP BY status"
    ).fetchall()
    conn.close()
    return {r["status"]: r["cnt"] for r in rows}


# ═══════════════════════════════════════════════════════════════════
# PAYMENT QUERIES
# ═══════════════════════════════════════════════════════════════════

def save_payment(order_id: int, user_id: int, method: str, screenshot_id: str, trx_ref=None):
    """Save payment screenshot submission."""
    conn = get_connection()
    conn.execute("""
        INSERT INTO payments (order_id, user_id, method, screenshot_id, transaction_ref)
        VALUES (?, ?, ?, ?, ?)
    """, (order_id, user_id, method, screenshot_id, trx_ref))
    conn.commit()
    conn.close()


def get_payment_for_order(order_id: int):
    """Get payment record for a specific order."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM payments WHERE order_id = ?", (order_id,)
    ).fetchone()
    conn.close()
    return row


# ═══════════════════════════════════════════════════════════════════
# COUPON QUERIES
# ═══════════════════════════════════════════════════════════════════

def validate_coupon(code: str):
    """
    Check if a coupon code is valid.
    Returns coupon row if valid, None otherwise.
    """
    conn = get_connection()
    row = conn.execute("""
        SELECT * FROM coupons
        WHERE code = ? AND is_active = 1
          AND used_count < max_uses
          AND (expires_at IS NULL OR expires_at > datetime('now'))
    """, (code.upper(),)).fetchone()
    conn.close()
    return row


def use_coupon(code: str):
    """Increment the used_count of a coupon."""
    conn = get_connection()
    conn.execute(
        "UPDATE coupons SET used_count = used_count + 1 WHERE code = ?",
        (code.upper(),)
    )
    conn.commit()
    conn.close()
