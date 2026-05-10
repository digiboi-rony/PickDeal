"""models/product.py"""
import json
from database.connection import get_conn


def get_categories():
    return get_conn().execute(
        "SELECT * FROM categories WHERE is_active=1 ORDER BY sort_order"
    ).fetchall()


def get_by_category(cat_id, page=0, per_page=5):
    offset = page * per_page
    return get_conn().execute("""
        SELECT p.*, c.emoji as cat_emoji
        FROM products p JOIN categories c ON p.cat_id=c.cat_id
        WHERE p.cat_id=? AND p.is_active=1
        ORDER BY p.is_featured DESC, p.sold_count DESC
        LIMIT ? OFFSET ?
    """, (cat_id, per_page, offset)).fetchall()


def count_by_category(cat_id):
    return get_conn().execute(
        "SELECT COUNT(*) FROM products WHERE cat_id=? AND is_active=1", (cat_id,)
    ).fetchone()[0]


def get(product_id):
    return get_conn().execute("""
        SELECT p.*, c.name as cat_name, c.emoji as cat_emoji
        FROM products p JOIN categories c ON p.cat_id=c.cat_id
        WHERE p.product_id=?
    """, (product_id,)).fetchone()


def get_images(product_id):
    return get_conn().execute(
        "SELECT file_id FROM product_images WHERE product_id=? ORDER BY sort_order",
        (product_id,)
    ).fetchall()


def search(query, page=0, per_page=5):
    q = f"%{query}%"
    offset = page * per_page
    return get_conn().execute("""
        SELECT p.*, c.emoji as cat_emoji
        FROM products p JOIN categories c ON p.cat_id=c.cat_id
        WHERE p.is_active=1 AND (p.name LIKE ? OR p.description LIKE ? OR p.tags LIKE ?)
        ORDER BY p.is_featured DESC
        LIMIT ? OFFSET ?
    """, (q, q, q, per_page, offset)).fetchall()


def get_featured():
    return get_conn().execute("""
        SELECT p.*, c.emoji as cat_emoji
        FROM products p JOIN categories c ON p.cat_id=c.cat_id
        WHERE p.is_featured=1 AND p.is_active=1
        ORDER BY p.sold_count DESC LIMIT 6
    """).fetchall()


def get_bestsellers():
    return get_conn().execute("""
        SELECT p.*, c.emoji as cat_emoji
        FROM products p JOIN categories c ON p.cat_id=c.cat_id
        WHERE p.is_bestseller=1 AND p.is_active=1
        ORDER BY p.sold_count DESC LIMIT 5
    """).fetchall()


def add_image(product_id, file_id, order=0):
    conn = get_conn()
    conn.execute(
        "INSERT INTO product_images(product_id,file_id,sort_order) VALUES(?,?,?)",
        (product_id, file_id, order)
    )
    conn.commit()


def create(cat_id, name, desc, price, disc_price, stock, tags=None):
    conn = get_conn()
    c = conn.execute("""
        INSERT INTO products(cat_id,name,description,price,discount_price,stock,tags)
        VALUES(?,?,?,?,?,?,?)
    """, (cat_id, name, desc, price, disc_price, stock, json.dumps(tags or [])))
    conn.commit()
    return c.lastrowid


def update_field(product_id, field, value):
    allowed = {"name","description","price","discount_price","stock","is_featured",
               "is_bestseller","is_active","cat_id"}
    if field not in allowed:
        raise ValueError(f"Field '{field}' not allowed")
    conn = get_conn()
    conn.execute(f"UPDATE products SET {field}=? WHERE product_id=?", (value, product_id))
    conn.commit()


def update_stock(product_id, qty_delta):
    conn = get_conn()
    conn.execute(
        "UPDATE products SET stock=MAX(0,stock+?), sold_count=sold_count+? WHERE product_id=?",
        (qty_delta, max(0, -qty_delta), product_id)
    )
    conn.commit()


def low_stock(threshold=5):
    return get_conn().execute(
        "SELECT * FROM products WHERE stock<=? AND is_active=1 AND stock>0", (threshold,)
    ).fetchall()


def out_of_stock():
    return get_conn().execute(
        "SELECT * FROM products WHERE stock=0 AND is_active=1"
    ).fetchall()


def delete(product_id):
    conn = get_conn()
    conn.execute("UPDATE products SET is_active=0 WHERE product_id=?", (product_id,))
    conn.commit()


def get_all_for_admin(page=0, per_page=8):
    offset = page * per_page
    return get_conn().execute("""
        SELECT p.*, c.name as cat_name
        FROM products p JOIN categories c ON p.cat_id=c.cat_id
        ORDER BY p.created_at DESC LIMIT ? OFFSET ?
    """, (per_page, offset)).fetchall()
