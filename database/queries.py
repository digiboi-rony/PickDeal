"""
database/queries.py
===================
All database operations — single source of truth for SQL.
Never write raw SQL in handlers.
"""

import logging
import sqlite3
from typing import Optional
from database.db_setup import get_connection

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# USER QUERIES
# ═══════════════════════════════════════════════════════════════════

def upsert_user(user_id: int, username: str, first_name: str, last_name: str):
    """Register or update user on every interaction."""
    import hashlib
    referral_code = hashlib.md5(str(user_id).encode()).hexdigest()[:8].upper()
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO users (user_id, username, first_name, last_name, referral_code, last_seen)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
                username   = excluded.username,
                first_name = excluded.first_name,
                last_name  = excluded.last_name,
                last_seen  = datetime('now')
        """, (user_id, username or "", first_name or "", last_name or "", referral_code))


def get_user(user_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()


def get_all_users() -> list[int]:
    with get_connection() as conn:
        rows = conn.execute("SELECT user_id FROM users WHERE is_banned = 0").fetchall()
        return [r["user_id"] for r in rows]


def get_user_count() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]


def ban_user(user_id: int):
    with get_connection() as conn:
        conn.execute("UPDATE users SET is_banned = 1 WHERE user_id = ?", (user_id,))


def unban_user(user_id: int):
    with get_connection() as conn:
        conn.execute("UPDATE users SET is_banned = 0 WHERE user_id = ?", (user_id,))


def update_user_stats(user_id: int, order_total: float):
    """Increment order count and total spent for a user."""
    with get_connection() as conn:
        conn.execute("""
            UPDATE users
            SET total_orders = total_orders + 1,
                total_spent  = total_spent + ?
            WHERE user_id = ?
        """, (order_total, user_id))


def get_top_customers(limit: int = 5) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT user_id, first_name, username, total_orders, total_spent
            FROM users ORDER BY total_spent DESC LIMIT ?
        """, (limit,)).fetchall()


# ═══════════════════════════════════════════════════════════════════
# CATEGORY QUERIES
# ═══════════════════════════════════════════════════════════════════

def get_categories() -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT c.*, COUNT(p.product_id) as product_count
            FROM categories c
            LEFT JOIN products p ON p.category = c.name AND p.is_active = 1
            WHERE c.is_active = 1
            GROUP BY c.category_id
            ORDER BY c.sort_order
        """).fetchall()


# ═══════════════════════════════════════════════════════════════════
# PRODUCT QUERIES
# ═══════════════════════════════════════════════════════════════════

def get_products_by_category(category: str, page: int = 0, per_page: int = 8) -> list:
    offset = page * per_page
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM products
            WHERE category = ? AND is_active = 1
            ORDER BY is_featured DESC, sold_count DESC, name
            LIMIT ? OFFSET ?
        """, (category, per_page, offset)).fetchall()


def count_products_by_category(category: str) -> int:
    with get_connection() as conn:
        return conn.execute(
            "SELECT COUNT(*) FROM products WHERE category=? AND is_active=1", (category,)
        ).fetchone()[0]


def get_product(product_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM products WHERE product_id = ?", (product_id,)).fetchone()


def get_featured_products(limit: int = 5) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM products WHERE is_active=1 AND is_featured=1
            ORDER BY sold_count DESC LIMIT ?
        """, (limit,)).fetchall()


def get_bestseller_products(limit: int = 5) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM products WHERE is_active=1 AND is_bestseller=1
            ORDER BY sold_count DESC LIMIT ?
        """, (limit,)).fetchall()


def search_products(query: str, limit: int = 10) -> list:
    q = f"%{query}%"
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM products
            WHERE is_active=1 AND (name LIKE ? OR description LIKE ? OR tags LIKE ?)
            ORDER BY is_featured DESC, sold_count DESC
            LIMIT ?
        """, (q, q, q, limit)).fetchall()


def add_product(name, category, description, price, discount_price,
                stock, image_url=None, tags="", is_featured=0) -> int:
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO products
                (name, category, description, price, discount_price, stock, image_url, tags, is_featured)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, (name, category, description, float(price), float(discount_price or price),
              int(stock), image_url, tags, is_featured))
        return cur.lastrowid


def update_product_field(product_id: int, field: str, value):
    """Safely update a single product field."""
    allowed = {"name", "price", "discount_price", "stock", "description",
               "is_active", "is_featured", "is_bestseller", "image_url", "category"}
    if field not in allowed:
        raise ValueError(f"Field '{field}' not allowed.")
    with get_connection() as conn:
        conn.execute(f"UPDATE products SET {field}=? WHERE product_id=?", (value, product_id))


def update_product_stock(product_id: int, qty_sold: int):
    with get_connection() as conn:
        conn.execute("""
            UPDATE products
            SET stock      = stock - ?,
                sold_count = sold_count + ?
            WHERE product_id = ?
        """, (qty_sold, qty_sold, product_id))


def delete_product(product_id: int):
    with get_connection() as conn:
        conn.execute("UPDATE products SET is_active=0 WHERE product_id=?", (product_id,))


def get_low_stock_products(threshold: int = 5) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM products WHERE is_active=1 AND stock <= ? ORDER BY stock
        """, (threshold,)).fetchall()


def get_all_products_admin(limit: int = 20, offset: int = 0) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM products ORDER BY created_at DESC LIMIT ? OFFSET ?
        """, (limit, offset)).fetchall()


def add_product_image(product_id: int, file_id: str, is_primary: bool = False):
    with get_connection() as conn:
        if is_primary:
            conn.execute("UPDATE product_images SET is_primary=0 WHERE product_id=?", (product_id,))
            conn.execute("UPDATE products SET image_url=? WHERE product_id=?", (file_id, product_id))
        conn.execute("""
            INSERT INTO product_images (product_id, file_id, is_primary)
            VALUES (?,?,?)
        """, (product_id, file_id, 1 if is_primary else 0))


# ═══════════════════════════════════════════════════════════════════
# CART QUERIES
# ═══════════════════════════════════════════════════════════════════

def get_or_create_cart(user_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT cart_id FROM carts WHERE user_id=?", (user_id,)).fetchone()
        if row:
            return row["cart_id"]
        cur = conn.execute("INSERT INTO carts (user_id) VALUES (?)", (user_id,))
        return cur.lastrowid


def add_to_cart(user_id: int, product_id: int, quantity: int = 1):
    cart_id = get_or_create_cart(user_id)
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO cart_items (cart_id, product_id, quantity)
            VALUES (?,?,?)
            ON CONFLICT(cart_id, product_id) DO UPDATE
            SET quantity = quantity + excluded.quantity
        """, (cart_id, product_id, quantity))


def remove_from_cart(user_id: int, product_id: int):
    cart_id = get_or_create_cart(user_id)
    with get_connection() as conn:
        conn.execute("DELETE FROM cart_items WHERE cart_id=? AND product_id=?", (cart_id, product_id))


def update_cart_quantity(user_id: int, product_id: int, quantity: int):
    cart_id = get_or_create_cart(user_id)
    with get_connection() as conn:
        if quantity <= 0:
            conn.execute("DELETE FROM cart_items WHERE cart_id=? AND product_id=?", (cart_id, product_id))
        else:
            conn.execute("""
                UPDATE cart_items SET quantity=? WHERE cart_id=? AND product_id=?
            """, (quantity, cart_id, product_id))


def get_cart_items(user_id: int) -> list:
    cart_id = get_or_create_cart(user_id)
    with get_connection() as conn:
        return conn.execute("""
            SELECT ci.*, p.name, p.price, p.discount_price, p.stock, p.image_url
            FROM cart_items ci
            JOIN products p ON ci.product_id = p.product_id
            WHERE ci.cart_id = ?
        """, (cart_id,)).fetchall()


def clear_cart(user_id: int):
    cart_id = get_or_create_cart(user_id)
    with get_connection() as conn:
        conn.execute("DELETE FROM cart_items WHERE cart_id=?", (cart_id,))


# ═══════════════════════════════════════════════════════════════════
# ORDER QUERIES
# ═══════════════════════════════════════════════════════════════════

def create_order(user_id, full_name, phone, address, delivery_area,
                 subtotal, delivery_charge, total_price, payment_method,
                 coupon_code=None, discount=0, notes=None) -> int:
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO orders
                (user_id, full_name, phone, address, delivery_area, subtotal,
                 delivery_charge, total_price, payment_method, coupon_code, discount, notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (user_id, full_name, phone, address, delivery_area, subtotal,
              delivery_charge, total_price, payment_method, coupon_code, discount, notes))
        return cur.lastrowid


def add_order_items(order_id: int, items: list):
    """items: list of dicts with product_id, product_name, quantity, unit_price"""
    rows = [
        (order_id, i["product_id"], i["product_name"], i["quantity"],
         i["unit_price"], i["quantity"] * i["unit_price"])
        for i in items
    ]
    with get_connection() as conn:
        conn.executemany("""
            INSERT INTO order_items
                (order_id, product_id, product_name, quantity, unit_price, total_price)
            VALUES (?,?,?,?,?,?)
        """, rows)


def get_order(order_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("""
            SELECT o.*,
                   u.first_name, u.username,
                   GROUP_CONCAT(oi.product_name || ' x' || oi.quantity, ', ') AS items_summary
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            LEFT JOIN order_items oi ON oi.order_id = o.order_id
            WHERE o.order_id = ?
            GROUP BY o.order_id
        """, (order_id,)).fetchone()


def get_order_items(order_id: int) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT oi.*, p.image_url
            FROM order_items oi
            LEFT JOIN products p ON oi.product_id = p.product_id
            WHERE oi.order_id = ?
        """, (order_id,)).fetchall()


def get_user_orders(user_id: int, limit: int = 10) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT o.*, GROUP_CONCAT(oi.product_name || ' x' || oi.quantity, ', ') AS items_summary
            FROM orders o
            LEFT JOIN order_items oi ON oi.order_id = o.order_id
            WHERE o.user_id = ?
            GROUP BY o.order_id
            ORDER BY o.created_at DESC
            LIMIT ?
        """, (user_id, limit)).fetchall()


def get_all_orders(status_filter=None, limit=20, offset=0) -> list:
    with get_connection() as conn:
        if status_filter and status_filter != "all":
            return conn.execute("""
                SELECT o.*, u.first_name, u.username,
                       GROUP_CONCAT(oi.product_name || ' x' || oi.quantity, ', ') AS items_summary
                FROM orders o
                JOIN users u ON o.user_id = u.user_id
                LEFT JOIN order_items oi ON oi.order_id = o.order_id
                WHERE o.status = ?
                GROUP BY o.order_id
                ORDER BY o.created_at DESC
                LIMIT ? OFFSET ?
            """, (status_filter, limit, offset)).fetchall()
        return conn.execute("""
            SELECT o.*, u.first_name, u.username,
                   GROUP_CONCAT(oi.product_name || ' x' || oi.quantity, ', ') AS items_summary
            FROM orders o
            JOIN users u ON o.user_id = u.user_id
            LEFT JOIN order_items oi ON oi.order_id = o.order_id
            GROUP BY o.order_id
            ORDER BY o.created_at DESC
            LIMIT ? OFFSET ?
        """, (limit, offset)).fetchall()


def update_order_status(order_id: int, new_status: str):
    with get_connection() as conn:
        conn.execute("""
            UPDATE orders
            SET status=?, updated_at=datetime('now')
            WHERE order_id=?
        """, (new_status, order_id))


def count_orders_by_status() -> dict:
    with get_connection() as conn:
        rows = conn.execute("SELECT status, COUNT(*) as cnt FROM orders GROUP BY status").fetchall()
        return {r["status"]: r["cnt"] for r in rows}


def get_revenue_stats() -> dict:
    with get_connection() as conn:
        row = conn.execute("""
            SELECT
                COUNT(*) as total_orders,
                COALESCE(SUM(total_price), 0) as total_revenue,
                COALESCE(SUM(CASE WHEN date(created_at)=date('now') THEN total_price ELSE 0 END), 0) as today_revenue,
                COALESCE(SUM(CASE WHEN status='delivered' THEN total_price ELSE 0 END), 0) as delivered_revenue
            FROM orders
            WHERE status != 'cancelled'
        """).fetchone()
        return dict(row) if row else {}


def get_top_products(limit: int = 5) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT p.name, SUM(oi.quantity) as total_sold, SUM(oi.total_price) as revenue
            FROM order_items oi
            JOIN products p ON oi.product_id = p.product_id
            JOIN orders o ON oi.order_id = o.order_id
            WHERE o.status != 'cancelled'
            GROUP BY oi.product_id
            ORDER BY total_sold DESC
            LIMIT ?
        """, (limit,)).fetchall()


# ═══════════════════════════════════════════════════════════════════
# PAYMENT QUERIES
# ═══════════════════════════════════════════════════════════════════

def save_payment(order_id: int, user_id: int, method: str,
                 screenshot_id: str, amount: float, trx_ref=None):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO payments (order_id, user_id, method, screenshot_id, amount, transaction_ref)
            VALUES (?,?,?,?,?,?)
        """, (order_id, user_id, method, screenshot_id, amount, trx_ref))


def verify_payment(payment_id: int, admin_id: int):
    with get_connection() as conn:
        conn.execute("""
            UPDATE payments
            SET status='verified', verified_at=datetime('now'), verified_by=?
            WHERE payment_id=?
        """, (admin_id, payment_id))


def get_payment_for_order(order_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM payments WHERE order_id=? ORDER BY submitted_at DESC LIMIT 1",
            (order_id,)
        ).fetchone()


# ═══════════════════════════════════════════════════════════════════
# COUPON QUERIES
# ═══════════════════════════════════════════════════════════════════

def validate_coupon(code: str, order_total: float = 0) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM coupons
            WHERE code=? AND is_active=1
              AND used_count < max_uses
              AND (expires_at IS NULL OR expires_at > datetime('now'))
              AND min_order <= ?
        """, (code.upper(), order_total)).fetchone()


def use_coupon(code: str):
    with get_connection() as conn:
        conn.execute("UPDATE coupons SET used_count=used_count+1 WHERE code=?", (code.upper(),))


def get_all_coupons() -> list:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM coupons ORDER BY created_at DESC").fetchall()


def create_coupon(code: str, discount_pct: float = 0, discount_flat: float = 0,
                  min_order: float = 0, max_uses: int = 100, expires_at: str = None):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO coupons (code, discount_pct, discount_flat, min_order, max_uses, expires_at)
            VALUES (?,?,?,?,?,?)
        """, (code.upper(), discount_pct, discount_flat, min_order, max_uses, expires_at))


# ═══════════════════════════════════════════════════════════════════
# WISHLIST QUERIES
# ═══════════════════════════════════════════════════════════════════

def add_to_wishlist(user_id: int, product_id: int):
    with get_connection() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO wishlist (user_id, product_id) VALUES (?,?)
        """, (user_id, product_id))


def remove_from_wishlist(user_id: int, product_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM wishlist WHERE user_id=? AND product_id=?", (user_id, product_id))


def get_wishlist(user_id: int) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT p.* FROM wishlist w
            JOIN products p ON w.product_id = p.product_id
            WHERE w.user_id = ? AND p.is_active = 1
            ORDER BY w.added_at DESC
        """, (user_id,)).fetchall()


def is_in_wishlist(user_id: int, product_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT 1 FROM wishlist WHERE user_id=? AND product_id=?", (user_id, product_id)
        ).fetchone()
        return row is not None


# ═══════════════════════════════════════════════════════════════════
# RECENTLY VIEWED QUERIES
# ═══════════════════════════════════════════════════════════════════

def add_recently_viewed(user_id: int, product_id: int):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO recently_viewed (user_id, product_id, viewed_at)
            VALUES (?,?,datetime('now'))
            ON CONFLICT(user_id, product_id) DO UPDATE SET viewed_at=datetime('now')
        """, (user_id, product_id))


def get_recently_viewed(user_id: int, limit: int = 5) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT p.* FROM recently_viewed rv
            JOIN products p ON rv.product_id = p.product_id
            WHERE rv.user_id = ? AND p.is_active = 1
            ORDER BY rv.viewed_at DESC LIMIT ?
        """, (user_id, limit)).fetchall()


# ═══════════════════════════════════════════════════════════════════
# SUPPORT TICKET QUERIES
# ═══════════════════════════════════════════════════════════════════

def create_ticket(user_id: int, message: str, order_id: int = None, subject: str = None) -> int:
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO support_tickets (user_id, order_id, subject, message)
            VALUES (?,?,?,?)
        """, (user_id, order_id, subject, message))
        return cur.lastrowid


def get_open_tickets(limit: int = 10) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT t.*, u.first_name, u.username
            FROM support_tickets t
            JOIN users u ON t.user_id = u.user_id
            WHERE t.status IN ('open', 'in_progress')
            ORDER BY t.created_at DESC LIMIT ?
        """, (limit,)).fetchall()


def reply_ticket(ticket_id: int, reply: str, admin_id: int):
    with get_connection() as conn:
        conn.execute("""
            UPDATE support_tickets
            SET reply=?, status='resolved', assigned_to=?, updated_at=datetime('now')
            WHERE ticket_id=?
        """, (reply, admin_id, ticket_id))


def get_user_tickets(user_id: int) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM support_tickets WHERE user_id=? ORDER BY created_at DESC LIMIT 10
        """, (user_id,)).fetchall()


# ═══════════════════════════════════════════════════════════════════
# ANALYTICS QUERIES
# ═══════════════════════════════════════════════════════════════════

def log_event(event_type: str, user_id: int = None, product_id: int = None,
              order_id: int = None, value: float = 0):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO analytics (event_type, user_id, product_id, order_id, value)
            VALUES (?,?,?,?,?)
        """, (event_type, user_id, product_id, order_id, value))


def get_daily_stats(days: int = 7) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT date(created_at) as day,
                   COUNT(*) as orders,
                   SUM(total_price) as revenue
            FROM orders
            WHERE created_at >= datetime('now', ? || ' days')
              AND status != 'cancelled'
            GROUP BY day ORDER BY day DESC
        """, (f"-{days}",)).fetchall()
