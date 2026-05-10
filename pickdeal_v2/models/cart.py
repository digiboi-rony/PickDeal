"""models/cart.py"""
from database.connection import get_conn


def _ensure_cart(user_id) -> int:
    conn = get_conn()
    conn.execute("INSERT OR IGNORE INTO carts(user_id) VALUES(?)", (user_id,))
    conn.commit()
    return conn.execute(
        "SELECT cart_id FROM carts WHERE user_id=?", (user_id,)
    ).fetchone()["cart_id"]


def add_item(user_id, product_id, qty=1):
    cart_id = _ensure_cart(user_id)
    conn = get_conn()
    conn.execute("""
        INSERT INTO cart_items(cart_id,product_id,quantity) VALUES(?,?,?)
        ON CONFLICT(cart_id,product_id)
        DO UPDATE SET quantity=quantity+excluded.quantity
    """, (cart_id, product_id, qty))
    conn.execute("UPDATE carts SET updated_at=datetime('now') WHERE cart_id=?", (cart_id,))
    conn.commit()


def remove_item(user_id, product_id):
    cart_id = _ensure_cart(user_id)
    conn = get_conn()
    conn.execute(
        "DELETE FROM cart_items WHERE cart_id=? AND product_id=?", (cart_id, product_id)
    )
    conn.commit()


def update_qty(user_id, product_id, qty):
    if qty <= 0:
        return remove_item(user_id, product_id)
    cart_id = _ensure_cart(user_id)
    conn = get_conn()
    conn.execute(
        "UPDATE cart_items SET quantity=? WHERE cart_id=? AND product_id=?",
        (qty, cart_id, product_id)
    )
    conn.commit()


def get_items(user_id):
    cart_id = _ensure_cart(user_id)
    return get_conn().execute("""
        SELECT ci.*, p.name, p.price, p.discount_price, p.stock,
               COALESCE(p.discount_price, p.price) as eff_price
        FROM cart_items ci
        JOIN products p ON ci.product_id=p.product_id
        WHERE ci.cart_id=?
    """, (cart_id,)).fetchall()


def clear(user_id):
    cart_id = _ensure_cart(user_id)
    conn = get_conn()
    conn.execute("DELETE FROM cart_items WHERE cart_id=?", (cart_id,))
    conn.commit()


def count_items(user_id) -> int:
    cart_id = _ensure_cart(user_id)
    row = get_conn().execute(
        "SELECT COALESCE(SUM(quantity),0) as n FROM cart_items WHERE cart_id=?", (cart_id,)
    ).fetchone()
    return int(row["n"]) if row else 0
