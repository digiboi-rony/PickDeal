"""
database/queries.py — PickDeal BD v3
Single source of truth for all SQL. No raw SQL in handlers.
Fixes: category CRUD, delivery/payment methods, coupon edit/delete.
"""

import logging
import sqlite3
from typing import Optional
from database.db_setup import get_connection

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════
# USERS
# ════════════════════════════════════════════════

def upsert_user(user_id: int, username: str, first_name: str, last_name: str):
    import hashlib
    ref = hashlib.md5(str(user_id).encode()).hexdigest()[:8].upper()
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO users (user_id, username, first_name, last_name, referral_code, last_seen)
            VALUES (?,?,?,?,?,datetime('now'))
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username, first_name=excluded.first_name,
                last_name=excluded.last_name, last_seen=datetime('now')
        """, (user_id, username or "", first_name or "", last_name or "", ref))


def get_user(user_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()


def get_all_user_ids() -> list[int]:
    with get_connection() as conn:
        rows = conn.execute("SELECT user_id FROM users WHERE is_banned=0").fetchall()
        return [r["user_id"] for r in rows]


def get_user_count() -> int:
    with get_connection() as conn:
        return conn.execute("SELECT COUNT(*) as cnt FROM users").fetchone()["cnt"]


def update_user_stats(user_id: int, order_total: float):
    with get_connection() as conn:
        conn.execute("""
            UPDATE users SET total_orders=total_orders+1, total_spent=total_spent+?
            WHERE user_id=?
        """, (order_total, user_id))


def get_top_customers(limit: int = 10) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT user_id,first_name,username,total_orders,total_spent
            FROM users ORDER BY total_spent DESC LIMIT ?
        """, (limit,)).fetchall()


def ban_user(user_id: int):
    with get_connection() as conn:
        conn.execute("UPDATE users SET is_banned=1 WHERE user_id=?", (user_id,))


def unban_user(user_id: int):
    with get_connection() as conn:
        conn.execute("UPDATE users SET is_banned=0 WHERE user_id=?", (user_id,))


# ════════════════════════════════════════════════
# CATEGORIES  (full CRUD)
# ════════════════════════════════════════════════

def get_categories(active_only: bool = True) -> list:
    with get_connection() as conn:
        where = "WHERE c.is_active=1" if active_only else ""
        return conn.execute(f"""
            SELECT c.*, COUNT(p.product_id) as product_count
            FROM categories c
            LEFT JOIN products p ON p.category=c.name AND p.is_active=1
            {where}
            GROUP BY c.category_id ORDER BY c.sort_order
        """).fetchall()


def get_category(category_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM categories WHERE category_id=?", (category_id,)
        ).fetchone()


def add_category(name: str, emoji: str = "🛍️", sort_order: int = 0) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO categories (name, emoji, sort_order) VALUES (?,?,?)",
            (name, emoji, sort_order)
        )
        return cur.lastrowid


def update_category(category_id: int, field: str, value):
    allowed = {"name", "emoji", "sort_order", "is_active", "is_featured"}
    if field not in allowed:
        raise ValueError(f"Field '{field}' not allowed.")
    with get_connection() as conn:
        conn.execute(
            f"UPDATE categories SET {field}=? WHERE category_id=?", (value, category_id)
        )


def delete_category(category_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM categories WHERE category_id=?", (category_id,))


# ════════════════════════════════════════════════
# PRODUCTS
# ════════════════════════════════════════════════

def get_products_by_category(category: str, page: int = 0, per_page: int = 6) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM products
            WHERE category=? AND is_active=1
            ORDER BY is_featured DESC, sold_count DESC, name
            LIMIT ? OFFSET ?
        """, (category, per_page, page * per_page)).fetchall()


def count_products_by_category(category: str) -> int:
    with get_connection() as conn:
        return conn.execute(
            "SELECT COUNT(*) as cnt FROM products WHERE category=? AND is_active=1", (category,)
        ).fetchone()["cnt"]


def get_product(product_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM products WHERE product_id=?", (product_id,)
        ).fetchone()


def get_product_images(product_id: int) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM product_images WHERE product_id=? ORDER BY is_primary DESC, sort_order
        """, (product_id,)).fetchall()


def get_featured_products(limit: int = 6) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM products WHERE is_active=1 AND is_featured=1
            ORDER BY sold_count DESC LIMIT ?
        """, (limit,)).fetchall()


def get_bestseller_products(limit: int = 6) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM products WHERE is_active=1 AND is_bestseller=1
            ORDER BY sold_count DESC LIMIT ?
        """, (limit,)).fetchall()


def get_new_arrivals(limit: int = 6) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM products WHERE is_active=1
            ORDER BY created_at DESC LIMIT ?
        """, (limit,)).fetchall()


def search_products(query: str, limit: int = 10) -> list:
    q = f"%{query}%"
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM products
            WHERE is_active=1 AND (name LIKE ? OR description LIKE ? OR tags LIKE ? OR category LIKE ?)
            ORDER BY is_featured DESC, sold_count DESC LIMIT ?
        """, (q, q, q, q, limit)).fetchall()


def add_product(name, category, description, price, discount_price,
                stock, image_url=None, tags="", is_featured=0,
                advance_pct=0, cod_available=1) -> int:
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO products
              (name,category,description,price,discount_price,stock,
               image_url,tags,is_featured,advance_pct,cod_available)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
        """, (name, category, description, float(price),
              float(discount_price or price), int(stock), image_url,
              tags, is_featured, advance_pct, cod_available))
        return cur.lastrowid


def update_product_field(product_id: int, field: str, value):
    allowed = {
        "name","price","discount_price","stock","description","is_active",
        "is_featured","is_bestseller","image_url","category","tags",
        "advance_pct","cod_available","rating"
    }
    if field not in allowed:
        raise ValueError(f"Field '{field}' not allowed.")
    with get_connection() as conn:
        conn.execute(f"UPDATE products SET {field}=? WHERE product_id=?", (value, product_id))


def update_product_stock(product_id: int, qty_sold: int):
    with get_connection() as conn:
        conn.execute("""
            UPDATE products SET stock=stock-?, sold_count=sold_count+?
            WHERE product_id=?
        """, (qty_sold, qty_sold, product_id))


def soft_delete_product(product_id: int):
    with get_connection() as conn:
        conn.execute("UPDATE products SET is_active=0 WHERE product_id=?", (product_id,))


def get_all_products_admin(limit: int = 10, offset: int = 0) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM products ORDER BY created_at DESC LIMIT ? OFFSET ?
        """, (limit, offset)).fetchall()


def get_low_stock_products(threshold: int = 10) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM products WHERE is_active=1 AND stock<=? ORDER BY stock
        """, (threshold,)).fetchall()


def add_product_image(product_id: int, file_id: str, is_primary: bool = False):
    with get_connection() as conn:
        if is_primary:
            conn.execute(
                "UPDATE product_images SET is_primary=0 WHERE product_id=?", (product_id,)
            )
            conn.execute(
                "UPDATE products SET image_url=? WHERE product_id=?", (file_id, product_id)
            )
        conn.execute("""
            INSERT INTO product_images (product_id, file_id, is_primary)
            VALUES (?,?,?)
        """, (product_id, file_id, 1 if is_primary else 0))


def delete_product_images(product_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM product_images WHERE product_id=?", (product_id,))


# ════════════════════════════════════════════════
# DELIVERY METHODS (full CRUD)
# ════════════════════════════════════════════════

def get_delivery_methods(active_only: bool = True) -> list:
    with get_connection() as conn:
        where = "WHERE is_active=1" if active_only else ""
        return conn.execute(
            f"SELECT * FROM delivery_methods {where} ORDER BY sort_order"
        ).fetchall()


def get_delivery_method(method_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM delivery_methods WHERE method_id=?", (method_id,)
        ).fetchone()


def get_delivery_by_name(name: str) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM delivery_methods WHERE name=?", (name,)
        ).fetchone()


def add_delivery_method(name: str, description: str, charge: float,
                         cod_allowed: bool = True) -> int:
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO delivery_methods (name, description, charge, cod_allowed)
            VALUES (?,?,?,?)
        """, (name, description, charge, 1 if cod_allowed else 0))
        return cur.lastrowid


def update_delivery_method(method_id: int, field: str, value):
    allowed = {"name","description","charge","cod_allowed","is_active","sort_order"}
    if field not in allowed:
        raise ValueError(f"Field '{field}' not allowed.")
    with get_connection() as conn:
        conn.execute(
            f"UPDATE delivery_methods SET {field}=? WHERE method_id=?", (value, method_id)
        )


def delete_delivery_method(method_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM delivery_methods WHERE method_id=?", (method_id,))


# ════════════════════════════════════════════════
# PAYMENT METHODS (full CRUD)
# ════════════════════════════════════════════════

def get_payment_methods(active_only: bool = True) -> list:
    with get_connection() as conn:
        where = "WHERE is_active=1" if active_only else ""
        return conn.execute(
            f"SELECT * FROM payment_methods {where} ORDER BY sort_order"
        ).fetchall()


def get_payment_method(method_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM payment_methods WHERE method_id=?", (method_id,)
        ).fetchone()


def update_payment_method(method_id: int, field: str, value):
    allowed = {"name","number","description","emoji","is_active","is_cod","sort_order"}
    if field not in allowed:
        raise ValueError(f"Field '{field}' not allowed.")
    with get_connection() as conn:
        conn.execute(
            f"UPDATE payment_methods SET {field}=? WHERE method_id=?", (value, method_id)
        )


def add_payment_method(name: str, number: str, description: str,
                        emoji: str = "💳", is_cod: bool = False) -> int:
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO payment_methods (name, number, description, emoji, is_cod)
            VALUES (?,?,?,?,?)
        """, (name, number, description, emoji, 1 if is_cod else 0))
        return cur.lastrowid


# ════════════════════════════════════════════════
# CART
# ════════════════════════════════════════════════

def get_or_create_cart(user_id: int) -> int:
    with get_connection() as conn:
        row = conn.execute("SELECT cart_id FROM carts WHERE user_id=?", (user_id,)).fetchone()
        if row:
            return row["cart_id"]
        return conn.execute("INSERT INTO carts (user_id) VALUES (?)", (user_id,)).lastrowid


def add_to_cart(user_id: int, product_id: int, quantity: int = 1):
    cart_id = get_or_create_cart(user_id)
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO cart_items (cart_id, product_id, quantity) VALUES (?,?,?)
            ON CONFLICT(cart_id, product_id) DO UPDATE SET quantity=quantity+excluded.quantity
        """, (cart_id, product_id, quantity))


def remove_from_cart(user_id: int, product_id: int):
    cart_id = get_or_create_cart(user_id)
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM cart_items WHERE cart_id=? AND product_id=?", (cart_id, product_id)
        )


def update_cart_quantity(user_id: int, product_id: int, quantity: int):
    cart_id = get_or_create_cart(user_id)
    with get_connection() as conn:
        if quantity <= 0:
            conn.execute(
                "DELETE FROM cart_items WHERE cart_id=? AND product_id=?", (cart_id, product_id)
            )
        else:
            conn.execute(
                "UPDATE cart_items SET quantity=? WHERE cart_id=? AND product_id=?",
                (quantity, cart_id, product_id)
            )


def get_cart_items(user_id: int) -> list:
    cart_id = get_or_create_cart(user_id)
    with get_connection() as conn:
        return conn.execute("""
            SELECT ci.*, p.name, p.price, p.discount_price, p.stock,
                   p.image_url, p.cod_available, p.advance_pct
            FROM cart_items ci
            JOIN products p ON ci.product_id=p.product_id
            WHERE ci.cart_id=?
        """, (cart_id,)).fetchall()


def clear_cart(user_id: int):
    cart_id = get_or_create_cart(user_id)
    with get_connection() as conn:
        conn.execute("DELETE FROM cart_items WHERE cart_id=?", (cart_id,))


# ════════════════════════════════════════════════
# ORDERS
# ════════════════════════════════════════════════

def create_order(user_id, full_name, phone, address, delivery_method,
                 delivery_charge, subtotal, total_price, payment_method,
                 advance_amount=0, coupon_code=None, discount=0, notes=None) -> int:
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO orders
              (user_id,full_name,phone,address,delivery_method,delivery_charge,
               subtotal,total_price,payment_method,advance_amount,
               coupon_code,discount,notes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (user_id, full_name, phone, address, delivery_method, delivery_charge,
              subtotal, total_price, payment_method, advance_amount,
              coupon_code, discount, notes))
        return cur.lastrowid


def add_order_items(order_id: int, items: list):
    rows = [(order_id, i["product_id"], i["product_name"],
             i["quantity"], i["unit_price"], i["quantity"] * i["unit_price"])
            for i in items]
    with get_connection() as conn:
        conn.executemany("""
            INSERT INTO order_items
              (order_id,product_id,product_name,quantity,unit_price,total_price)
            VALUES (?,?,?,?,?,?)
        """, rows)


def get_order(order_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("""
            SELECT o.*, u.first_name, u.username,
                   GROUP_CONCAT(oi.product_name||' x'||oi.quantity, ', ') AS items_summary
            FROM orders o
            JOIN users u ON o.user_id=u.user_id
            LEFT JOIN order_items oi ON oi.order_id=o.order_id
            WHERE o.order_id=? GROUP BY o.order_id
        """, (order_id,)).fetchone()


def get_order_items(order_id: int) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT oi.*, p.image_url FROM order_items oi
            LEFT JOIN products p ON oi.product_id=p.product_id
            WHERE oi.order_id=?
        """, (order_id,)).fetchall()


def get_user_orders(user_id: int, limit: int = 10) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT o.*,
                   GROUP_CONCAT(oi.product_name||' x'||oi.quantity, ', ') AS items_summary
            FROM orders o
            LEFT JOIN order_items oi ON oi.order_id=o.order_id
            WHERE o.user_id=?
            GROUP BY o.order_id ORDER BY o.created_at DESC LIMIT ?
        """, (user_id, limit)).fetchall()


def get_all_orders(status_filter=None, limit=10, offset=0) -> list:
    with get_connection() as conn:
        if status_filter and status_filter != "all":
            return conn.execute("""
                SELECT o.*, u.first_name, u.username,
                       GROUP_CONCAT(oi.product_name||' x'||oi.quantity, ', ') AS items_summary
                FROM orders o JOIN users u ON o.user_id=u.user_id
                LEFT JOIN order_items oi ON oi.order_id=o.order_id
                WHERE o.status=? GROUP BY o.order_id
                ORDER BY o.created_at DESC LIMIT ? OFFSET ?
            """, (status_filter, limit, offset)).fetchall()
        return conn.execute("""
            SELECT o.*, u.first_name, u.username,
                   GROUP_CONCAT(oi.product_name||' x'||oi.quantity, ', ') AS items_summary
            FROM orders o JOIN users u ON o.user_id=u.user_id
            LEFT JOIN order_items oi ON oi.order_id=o.order_id
            GROUP BY o.order_id ORDER BY o.created_at DESC LIMIT ? OFFSET ?
        """, (limit, offset)).fetchall()


def update_order_status(order_id: int, new_status: str, admin_note: str = None):
    with get_connection() as conn:
        conn.execute("""
            UPDATE orders SET status=?, updated_at=datetime('now'),
            admin_note=COALESCE(?, admin_note)
            WHERE order_id=?
        """, (new_status, admin_note, order_id))


def count_orders_by_status() -> dict:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) as cnt FROM orders GROUP BY status"
        ).fetchall()
        return {r["status"]: r["cnt"] for r in rows}


def get_revenue_stats() -> dict:
    with get_connection() as conn:
        row = conn.execute("""
            SELECT COUNT(*) as total_orders,
                   COALESCE(SUM(total_price),0) as total_revenue,
                   COALESCE(SUM(CASE WHEN date(created_at)=date('now') THEN total_price ELSE 0 END),0) as today_revenue,
                   COALESCE(SUM(CASE WHEN status='delivered' THEN total_price ELSE 0 END),0) as delivered_revenue
            FROM orders WHERE status!='cancelled'
        """).fetchone()
        return row if row else {}


def get_top_products(limit: int = 5) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT p.name, SUM(oi.quantity) as total_sold, SUM(oi.total_price) as revenue
            FROM order_items oi JOIN products p ON oi.product_id=p.product_id
            JOIN orders o ON oi.order_id=o.order_id
            WHERE o.status!='cancelled'
            GROUP BY oi.product_id ORDER BY total_sold DESC LIMIT ?
        """, (limit,)).fetchall()


def get_daily_stats(days: int = 7) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT date(created_at) as day, COUNT(*) as orders, SUM(total_price) as revenue
            FROM orders WHERE created_at>=datetime('now',? ||' days') AND status!='cancelled'
            GROUP BY day ORDER BY day DESC
        """, (f"-{days}",)).fetchall()


# ════════════════════════════════════════════════
# PAYMENTS
# ════════════════════════════════════════════════

def save_payment(order_id, user_id, method, screenshot_id, amount, trx_ref=None):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO payments (order_id,user_id,method,screenshot_id,amount,transaction_ref)
            VALUES (?,?,?,?,?,?)
        """, (order_id, user_id, method, screenshot_id, amount, trx_ref))


def get_payment_for_order(order_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM payments WHERE order_id=? ORDER BY submitted_at DESC LIMIT 1",
            (order_id,)
        ).fetchone()


# ════════════════════════════════════════════════
# COUPONS (full CRUD with edit/delete)
# ════════════════════════════════════════════════

def validate_coupon(code: str, order_total: float = 0) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM coupons
            WHERE code=? AND is_active=1 AND used_count<max_uses
              AND (expires_at IS NULL OR expires_at>datetime('now'))
              AND min_order<=?
        """, (code.upper(), order_total)).fetchone()


def use_coupon(code: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE coupons SET used_count=used_count+1 WHERE code=?", (code.upper(),)
        )


def get_all_coupons() -> list:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM coupons ORDER BY created_at DESC").fetchall()


def get_coupon(coupon_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("SELECT * FROM coupons WHERE coupon_id=?", (coupon_id,)).fetchone()


def create_coupon(code: str, discount_type: str = "percent", discount_val: float = 0,
                  min_order: float = 0, max_uses: int = 100, expires_at: str = None):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO coupons (code,discount_type,discount_val,min_order,max_uses,expires_at)
            VALUES (?,?,?,?,?,?)
        """, (code.upper(), discount_type, discount_val, min_order, max_uses, expires_at))


def update_coupon(coupon_id: int, field: str, value):
    allowed = {"code","discount_type","discount_val","min_order","max_uses","is_active","expires_at"}
    if field not in allowed:
        raise ValueError(f"Field '{field}' not allowed.")
    with get_connection() as conn:
        conn.execute(f"UPDATE coupons SET {field}=? WHERE coupon_id=?", (value, coupon_id))


def delete_coupon(coupon_id: int):
    with get_connection() as conn:
        conn.execute("DELETE FROM coupons WHERE coupon_id=?", (coupon_id,))


def calculate_coupon_discount(coupon, subtotal: float) -> float:
    if not coupon:
        return 0.0
    if coupon["discount_type"] == "percent":
        return round(subtotal * coupon["discount_val"] / 100, 2)
    return round(min(coupon["discount_val"], subtotal), 2)


# ════════════════════════════════════════════════
# WISHLIST
# ════════════════════════════════════════════════

def add_to_wishlist(user_id: int, product_id: int):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO wishlist (user_id,product_id) VALUES (?,?)",
            (user_id, product_id)
        )


def remove_from_wishlist(user_id: int, product_id: int):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM wishlist WHERE user_id=? AND product_id=?", (user_id, product_id)
        )


def is_in_wishlist(user_id: int, product_id: int) -> bool:
    with get_connection() as conn:
        return conn.execute(
            "SELECT 1 FROM wishlist WHERE user_id=? AND product_id=?", (user_id, product_id)
        ).fetchone() is not None


def get_wishlist(user_id: int) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT p.* FROM wishlist w JOIN products p ON w.product_id=p.product_id
            WHERE w.user_id=? AND p.is_active=1 ORDER BY w.added_at DESC
        """, (user_id,)).fetchall()


# ════════════════════════════════════════════════
# RECENTLY VIEWED
# ════════════════════════════════════════════════

def add_recently_viewed(user_id: int, product_id: int):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO recently_viewed (user_id,product_id,viewed_at)
            VALUES (?,?,datetime('now'))
            ON CONFLICT(user_id,product_id) DO UPDATE SET viewed_at=datetime('now')
        """, (user_id, product_id))


def get_recently_viewed(user_id: int, limit: int = 6) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT p.* FROM recently_viewed rv JOIN products p ON rv.product_id=p.product_id
            WHERE rv.user_id=? AND p.is_active=1
            ORDER BY rv.viewed_at DESC LIMIT ?
        """, (user_id, limit)).fetchall()


# ════════════════════════════════════════════════
# SUPPORT TICKETS
# ════════════════════════════════════════════════

def create_ticket(user_id: int, message: str, order_id: int = None,
                   subject: str = None) -> int:
    with get_connection() as conn:
        cur = conn.execute("""
            INSERT INTO support_tickets (user_id,order_id,subject,message)
            VALUES (?,?,?,?)
        """, (user_id, order_id, subject, message))
        return cur.lastrowid


def get_open_tickets(limit: int = 20) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT t.*, u.first_name, u.username
            FROM support_tickets t JOIN users u ON t.user_id=u.user_id
            WHERE t.status IN ('open','in_progress')
            ORDER BY t.created_at DESC LIMIT ?
        """, (limit,)).fetchall()


def get_all_tickets(limit: int = 20, offset: int = 0) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT t.*, u.first_name, u.username
            FROM support_tickets t JOIN users u ON t.user_id=u.user_id
            ORDER BY t.created_at DESC LIMIT ? OFFSET ?
        """, (limit, offset)).fetchall()


def get_ticket(ticket_id: int) -> Optional[sqlite3.Row]:
    with get_connection() as conn:
        return conn.execute("""
            SELECT t.*, u.first_name, u.username
            FROM support_tickets t JOIN users u ON t.user_id=u.user_id
            WHERE t.ticket_id=?
        """, (ticket_id,)).fetchone()


def reply_ticket(ticket_id: int, reply: str, admin_id: int):
    with get_connection() as conn:
        conn.execute("""
            UPDATE support_tickets
            SET reply=?, status='resolved', assigned_to=?, updated_at=datetime('now')
            WHERE ticket_id=?
        """, (reply, admin_id, ticket_id))


def set_ticket_status(ticket_id: int, status: str):
    with get_connection() as conn:
        conn.execute("""
            UPDATE support_tickets SET status=?, updated_at=datetime('now')
            WHERE ticket_id=?
        """, (status, ticket_id))


def get_user_tickets(user_id: int) -> list:
    with get_connection() as conn:
        return conn.execute("""
            SELECT * FROM support_tickets WHERE user_id=? ORDER BY created_at DESC LIMIT 10
        """, (user_id,)).fetchall()



# ════════════════════════════════════════════════
# ORDER REVIEWS / RATINGS
# ════════════════════════════════════════════════

def create_review(order_id: int, user_id: int, rating: int, note: str = None):
    with get_connection() as conn:
        conn.execute("""
            INSERT OR IGNORE INTO order_reviews (order_id, user_id, rating, note)
            VALUES (?,?,?,?)
        """, (order_id, user_id, rating, note))


def get_review_by_order(order_id: int) -> dict:
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM order_reviews WHERE order_id=?", (order_id,)
        ).fetchone()


def get_avg_rating() -> float:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT COALESCE(AVG(rating),0) as avg_r FROM order_reviews"
        ).fetchone()
        return round(row["avg_r"], 1) if row else 0.0


# ════════════════════════════════════════════════
# ANALYTICS
# ════════════════════════════════════════════════

def log_event(event_type: str, user_id: int = None, product_id: int = None,
               order_id: int = None, value: float = 0):
    with get_connection() as conn:
        conn.execute("""
            INSERT INTO analytics (event_type,user_id,product_id,order_id,value)
            VALUES (?,?,?,?,?)
        """, (event_type, user_id, product_id, order_id, value))
