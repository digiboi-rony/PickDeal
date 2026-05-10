"""
database/db_setup.py — PickDeal BD v3
Full schema: 18 tables, WAL mode, indexes, seed data.
Fixes: added delivery_methods, payment_methods tables.
"""

import sqlite3
import logging
import os
from config.settings import DB_PATH

logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA cache_size = -8000")
    return conn


def initialize_database():
    conn = get_connection()
    cur  = conn.cursor()

    # ── users ─────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id        INTEGER PRIMARY KEY,
            username       TEXT DEFAULT '',
            first_name     TEXT DEFAULT '',
            last_name      TEXT DEFAULT '',
            phone          TEXT,
            language       TEXT DEFAULT 'bn',
            is_banned      INTEGER DEFAULT 0,
            referral_by    INTEGER,
            referral_code  TEXT UNIQUE,
            referral_count INTEGER DEFAULT 0,
            total_orders   INTEGER DEFAULT 0,
            total_spent    REAL    DEFAULT 0,
            joined_at      TEXT    DEFAULT (datetime('now')),
            last_seen      TEXT    DEFAULT (datetime('now'))
        )
    """)

    # ── admins ────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id   INTEGER PRIMARY KEY,
            role      TEXT DEFAULT 'support',
            added_by  INTEGER,
            added_at  TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── categories ────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            category_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT UNIQUE NOT NULL,
            emoji        TEXT DEFAULT '🛍️',
            sort_order   INTEGER DEFAULT 0,
            is_active    INTEGER DEFAULT 1,
            is_featured  INTEGER DEFAULT 0
        )
    """)

    # ── products ──────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            name            TEXT NOT NULL,
            category_id     INTEGER,
            category        TEXT NOT NULL,
            description     TEXT DEFAULT '',
            price           REAL NOT NULL,
            discount_price  REAL,
            stock           INTEGER DEFAULT 0,
            image_url       TEXT,
            rating          REAL DEFAULT 0,
            review_count    INTEGER DEFAULT 0,
            is_active       INTEGER DEFAULT 1,
            is_featured     INTEGER DEFAULT 0,
            is_bestseller   INTEGER DEFAULT 0,
            tags            TEXT DEFAULT '',
            sold_count      INTEGER DEFAULT 0,
            advance_pct     REAL DEFAULT 0,
            cod_available   INTEGER DEFAULT 1,
            created_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (category_id) REFERENCES categories(category_id)
        )
    """)

    # ── product_images ────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS product_images (
            image_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id  INTEGER NOT NULL,
            file_id     TEXT NOT NULL,
            is_primary  INTEGER DEFAULT 0,
            sort_order  INTEGER DEFAULT 0,
            FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
        )
    """)

    # ── delivery_methods ──────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS delivery_methods (
            method_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT UNIQUE NOT NULL,
            description  TEXT DEFAULT '',
            charge       REAL NOT NULL DEFAULT 0,
            cod_allowed  INTEGER DEFAULT 1,
            is_active    INTEGER DEFAULT 1,
            sort_order   INTEGER DEFAULT 0
        )
    """)

    # ── payment_methods ───────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payment_methods (
            method_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT UNIQUE NOT NULL,
            number       TEXT DEFAULT '',
            description  TEXT DEFAULT '',
            emoji        TEXT DEFAULT '💳',
            is_active    INTEGER DEFAULT 1,
            is_cod       INTEGER DEFAULT 0,
            sort_order   INTEGER DEFAULT 0
        )
    """)

    # ── carts / cart_items ────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS carts (
            cart_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER UNIQUE NOT NULL,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS cart_items (
            item_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            cart_id    INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity   INTEGER DEFAULT 1,
            added_at   TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (cart_id)    REFERENCES carts(cart_id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(product_id),
            UNIQUE(cart_id, product_id)
        )
    """)

    # ── orders / order_items ──────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id          INTEGER NOT NULL,
            full_name        TEXT NOT NULL,
            phone            TEXT NOT NULL,
            address          TEXT NOT NULL,
            delivery_method  TEXT DEFAULT 'Outside Dhaka',
            delivery_charge  REAL DEFAULT 0,
            notes            TEXT,
            coupon_code      TEXT,
            discount         REAL DEFAULT 0,
            subtotal         REAL NOT NULL,
            advance_amount   REAL DEFAULT 0,
            total_price      REAL NOT NULL,
            payment_method   TEXT DEFAULT 'bkash',
            status           TEXT DEFAULT 'pending',
            admin_note       TEXT,
            created_at       TEXT DEFAULT (datetime('now')),
            updated_at       TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            item_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id     INTEGER NOT NULL,
            product_id   INTEGER NOT NULL,
            product_name TEXT NOT NULL,
            quantity     INTEGER NOT NULL,
            unit_price   REAL NOT NULL,
            total_price  REAL NOT NULL,
            FOREIGN KEY (order_id)   REFERENCES orders(order_id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)

    # ── payments ──────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            payment_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id        INTEGER NOT NULL,
            user_id         INTEGER NOT NULL,
            method          TEXT,
            transaction_ref TEXT,
            screenshot_id   TEXT,
            amount          REAL,
            status          TEXT DEFAULT 'pending',
            submitted_at    TEXT DEFAULT (datetime('now')),
            verified_at     TEXT,
            verified_by     INTEGER,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )
    """)

    # ── coupons ───────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS coupons (
            coupon_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            code          TEXT UNIQUE NOT NULL,
            discount_type TEXT DEFAULT 'percent',
            discount_val  REAL DEFAULT 0,
            min_order     REAL DEFAULT 0,
            max_uses      INTEGER DEFAULT 100,
            used_count    INTEGER DEFAULT 0,
            is_active     INTEGER DEFAULT 1,
            expires_at    TEXT,
            created_at    TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── wishlist ──────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS wishlist (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            product_id  INTEGER NOT NULL,
            added_at    TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, product_id),
            FOREIGN KEY (user_id)    REFERENCES users(user_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)

    # ── recently_viewed ───────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS recently_viewed (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            product_id  INTEGER NOT NULL,
            viewed_at   TEXT DEFAULT (datetime('now')),
            UNIQUE(user_id, product_id),
            FOREIGN KEY (user_id)    REFERENCES users(user_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)

    # ── support_tickets ───────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS support_tickets (
            ticket_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            order_id     INTEGER,
            subject      TEXT,
            message      TEXT NOT NULL,
            status       TEXT DEFAULT 'open',
            assigned_to  INTEGER,
            reply        TEXT,
            created_at   TEXT DEFAULT (datetime('now')),
            updated_at   TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    # ── notifications ─────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            type       TEXT,
            title      TEXT,
            message    TEXT,
            is_read    INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── broadcasts ────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS broadcasts (
            broadcast_id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id     INTEGER,
            target_user  INTEGER,
            message      TEXT NOT NULL,
            total_sent   INTEGER DEFAULT 0,
            total_failed INTEGER DEFAULT 0,
            sent_at      TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── analytics ─────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS analytics (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type  TEXT NOT NULL,
            user_id     INTEGER,
            product_id  INTEGER,
            order_id    INTEGER,
            value       REAL DEFAULT 0,
            extra       TEXT,
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)

    # ── indexes ───────────────────────────────────────────────────
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_orders_user    ON orders(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_orders_status  ON orders(status)",
        "CREATE INDEX IF NOT EXISTS idx_orders_date    ON orders(created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_products_cat   ON products(category)",
        "CREATE INDEX IF NOT EXISTS idx_products_act   ON products(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_cart_user      ON carts(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_wish_user      ON wishlist(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_rv_user        ON recently_viewed(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_tickets_status ON support_tickets(status)",
        "CREATE INDEX IF NOT EXISTS idx_analytics_ev   ON analytics(event_type)",
    ]
    for idx in indexes:
        cur.execute(idx)

    conn.commit()
    logger.info("✅ Database schema initialized.")

    _seed_all(conn)
    conn.close()


def _seed_all(conn):
    _seed_categories(conn)
    _seed_delivery_methods(conn)
    _seed_payment_methods(conn)
    _seed_products(conn)
    _seed_coupons(conn)


def _seed_categories(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM categories")
    if cur.fetchone()[0] > 0:
        return
    cats = [
        ("Fashion",      "👗", 1, 1),
        ("Gadgets",      "📱", 2, 1),
        ("Umbrellas",    "☂️", 3, 0),
        ("Offers",       "🔥", 4, 1),
        ("New Arrivals", "✨", 5, 0),
        ("Accessories",  "👜", 6, 0),
        ("Home & Living","🏠", 7, 0),
    ]
    cur.executemany(
        "INSERT INTO categories (name, emoji, sort_order, is_featured) VALUES (?,?,?,?)", cats
    )
    conn.commit()
    logger.info("🌱 Categories seeded.")


def _seed_delivery_methods(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM delivery_methods")
    if cur.fetchone()[0] > 0:
        return
    methods = [
        ("Inside Dhaka",   "ঢাকার ভেতরে ডেলিভারি (১-২ দিন)",    60,  1, 1, 1),
        ("Outside Dhaka",  "ঢাকার বাইরে ডেলিভারি (২-৪ দিন)",    120, 1, 1, 2),
        ("Express Dhaka",  "এক্সপ্রেস ডেলিভারি (সেইম ডে)",       150, 0, 1, 3),
        ("Pickup Point",   "আমাদের অফিস থেকে নিজে নিন",           0,  1, 1, 4),
    ]
    cur.executemany("""
        INSERT INTO delivery_methods (name, description, charge, cod_allowed, is_active, sort_order)
        VALUES (?,?,?,?,?,?)
    """, methods)
    conn.commit()
    logger.info("🌱 Delivery methods seeded.")


def _seed_payment_methods(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM payment_methods")
    if cur.fetchone()[0] > 0:
        return
    from config.settings import BKASH_NUMBER, NAGAD_NUMBER, ROCKET_NUMBER
    methods = [
        ("bKash",              BKASH_NUMBER,  "Send Money করুন", "💜", 1, 0, 1),
        ("Nagad",              NAGAD_NUMBER,  "Send Money করুন", "🟠", 1, 0, 2),
        ("Rocket",             ROCKET_NUMBER, "Send Money করুন", "🟣", 1, 0, 3),
        ("Cash on Delivery",   "",            "পণ্য পাওয়ার সময় দিন", "💵", 1, 1, 4),
    ]
    cur.executemany("""
        INSERT INTO payment_methods (name, number, description, emoji, is_active, is_cod, sort_order)
        VALUES (?,?,?,?,?,?,?)
    """, methods)
    conn.commit()
    logger.info("🌱 Payment methods seeded.")


def _seed_products(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM products")
    if cur.fetchone()[0] > 0:
        return
    products = [
        ("Smart Watch Pro X",      "Gadgets",    "⌚ Premium smartwatch, heart rate, sleep tracker, 7-day battery, IP67. Android & iOS.", 1499, 1299, 50, 4.5, 1, 1),
        ("Premium Travel Umbrella","Umbrellas",  "☂️ Double-layer windproof, auto open/close, UV protection, 10-rib, lifetime warranty.", 449, 349,  80, 4.7, 1, 0),
        ("Bluetooth Speaker X9",   "Gadgets",    "🔊 360° sound, 20W, IPX5, 12hr battery, TWS pairing, LED ring.",                       899, 749,  30, 4.3, 0, 1),
        ("Premium Cotton T-Shirt", "Fashion",    "👕 100% Supima cotton. S/M/L/XL/XXL. White/Black/Navy/Red/Olive.",                     349, 299, 200, 4.6, 0, 1),
        ("Wireless Earbuds Pro",   "Gadgets",    "🎧 ANC, 30hr total, IPX4, touch controls, low-latency gaming mode.",                   1299, 999, 40, 4.8, 1, 1),
        ("Leather Bifold Wallet",  "Accessories","👛 Full-grain leather, RFID block, 8 card slots, gift-boxed.",                          649, 549,  75, 4.4, 0, 0),
        ("Summer Floral Dress",    "Fashion",    "👗 Light chiffon, floral print. S/M/L/XL. Perfect casual & semi-formal.",              599, 499,  60, 4.5, 1, 0),
        ("Compact Umbrella",       "Umbrellas",  "☂️ Ultra-compact, windproof 8-rib, UV-coated. 10 colors.",                             299, 249, 120, 4.2, 0, 0),
    ]
    cur.executemany("""
        INSERT INTO products (name, category, description, price, discount_price, stock, rating, is_featured, is_bestseller)
        VALUES (?,?,?,?,?,?,?,?,?)
    """, products)
    conn.commit()
    logger.info("🌱 Products seeded.")


def _seed_coupons(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM coupons")
    if cur.fetchone()[0] > 0:
        return
    coupons = [
        ("PICKDEAL10", "percent", 10,  500,  1000),
        ("WELCOME50",  "flat",    50,  300,  500),
        ("EIDMUBARAK", "percent", 15,  800,  200),
    ]
    cur.executemany("""
        INSERT INTO coupons (code, discount_type, discount_val, min_order, max_uses)
        VALUES (?,?,?,?,?)
    """, coupons)
    conn.commit()
    logger.info("🌱 Coupons seeded.")
