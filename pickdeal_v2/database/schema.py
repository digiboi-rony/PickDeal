"""database/schema.py — all CREATE TABLE statements"""
import logging
from database.connection import get_conn

logger = logging.getLogger(__name__)

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    user_id     INTEGER PRIMARY KEY,
    username    TEXT,
    first_name  TEXT,
    last_name   TEXT,
    phone       TEXT,
    language    TEXT DEFAULT 'bn',
    is_banned   INTEGER DEFAULT 0,
    referral_by INTEGER,
    ref_code    TEXT UNIQUE,
    total_spent REAL DEFAULT 0,
    joined_at   TEXT DEFAULT (datetime('now')),
    last_seen   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS categories (
    cat_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT UNIQUE NOT NULL,
    emoji       TEXT DEFAULT '🛍️',
    description TEXT,
    sort_order  INTEGER DEFAULT 0,
    is_active   INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS products (
    product_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    cat_id        INTEGER NOT NULL,
    name          TEXT NOT NULL,
    description   TEXT,
    price         REAL NOT NULL,
    discount_price REAL,
    stock         INTEGER DEFAULT 0,
    sold_count    INTEGER DEFAULT 0,
    rating        REAL DEFAULT 0,
    tags          TEXT,
    is_featured   INTEGER DEFAULT 0,
    is_bestseller INTEGER DEFAULT 0,
    is_active     INTEGER DEFAULT 1,
    created_at    TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (cat_id) REFERENCES categories(cat_id)
);

CREATE TABLE IF NOT EXISTS product_images (
    img_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    file_id    TEXT NOT NULL,
    sort_order INTEGER DEFAULT 0,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS carts (
    cart_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER UNIQUE NOT NULL,
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS cart_items (
    item_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    cart_id    INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity   INTEGER DEFAULT 1,
    UNIQUE(cart_id, product_id),
    FOREIGN KEY (cart_id)    REFERENCES carts(cart_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS orders (
    order_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id        INTEGER NOT NULL,
    full_name      TEXT NOT NULL,
    phone          TEXT NOT NULL,
    address        TEXT NOT NULL,
    area           TEXT DEFAULT 'outside',
    notes          TEXT,
    subtotal       REAL NOT NULL,
    delivery_fee   REAL DEFAULT 60,
    discount       REAL DEFAULT 0,
    total          REAL NOT NULL,
    coupon_code    TEXT,
    payment_method TEXT DEFAULT 'bkash',
    status         TEXT DEFAULT 'pending',
    created_at     TEXT DEFAULT (datetime('now')),
    updated_at     TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS order_items (
    oi_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id     INTEGER NOT NULL,
    product_id   INTEGER NOT NULL,
    product_name TEXT NOT NULL,
    quantity     INTEGER NOT NULL,
    unit_price   REAL NOT NULL,
    total_price  REAL NOT NULL,
    FOREIGN KEY (order_id)   REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS payments (
    pay_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id      INTEGER NOT NULL UNIQUE,
    user_id       INTEGER NOT NULL,
    method        TEXT,
    trx_ref       TEXT,
    screenshot_id TEXT,
    status        TEXT DEFAULT 'pending',
    submitted_at  TEXT DEFAULT (datetime('now')),
    verified_at   TEXT,
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
);

CREATE TABLE IF NOT EXISTS coupons (
    coupon_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    code       TEXT UNIQUE NOT NULL,
    type       TEXT DEFAULT 'percent',
    value      REAL NOT NULL,
    min_order  REAL DEFAULT 0,
    max_uses   INTEGER DEFAULT 100,
    used_count INTEGER DEFAULT 0,
    is_active  INTEGER DEFAULT 1,
    expires_at TEXT
);

CREATE TABLE IF NOT EXISTS wishlist (
    wish_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    added_at   TEXT DEFAULT (datetime('now')),
    UNIQUE(user_id, product_id),
    FOREIGN KEY (user_id)    REFERENCES users(user_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id)
);

CREATE TABLE IF NOT EXISTS support_tickets (
    ticket_id  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    subject    TEXT,
    message    TEXT NOT NULL,
    status     TEXT DEFAULT 'open',
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

CREATE TABLE IF NOT EXISTS notifications (
    notif_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    type       TEXT,
    message    TEXT,
    sent_at    TEXT DEFAULT (datetime('now')),
    is_sent    INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS analytics (
    event_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER,
    event_type TEXT,
    meta       TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_orders_user   ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_products_cat  ON products(cat_id);
CREATE INDEX IF NOT EXISTS idx_cart_user     ON carts(user_id);
"""


def initialize():
    conn = get_conn()
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    logger.info("✅ Database schema initialized.")
