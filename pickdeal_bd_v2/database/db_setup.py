"""
database/db_setup.py
====================
SQLite database initialization with full schema for all features.
Upgrade-ready: schema mirrors what PostgreSQL would use.
"""

import sqlite3
import logging
import os
from config.settings import DB_PATH

logger = logging.getLogger(__name__)


def get_connection() -> sqlite3.Connection:
    """Thread-safe SQLite connection with WAL mode for concurrency."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")   # Better concurrency
    conn.execute("PRAGMA synchronous = NORMAL")  # Balance safety/speed
    conn.execute("PRAGMA cache_size = -8000")    # 8MB cache
    return conn


def initialize_database():
    """Create all tables, indexes, and seed data. Safe to run repeatedly."""
    conn = get_connection()
    cur = conn.cursor()

    # ─── Users ───────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id      INTEGER PRIMARY KEY,
            username     TEXT,
            first_name   TEXT,
            last_name    TEXT,
            phone        TEXT,
            language     TEXT DEFAULT 'en',
            is_banned    INTEGER DEFAULT 0,
            referral_by  INTEGER,
            referral_code TEXT UNIQUE,
            referral_count INTEGER DEFAULT 0,
            total_orders INTEGER DEFAULT 0,
            total_spent  REAL DEFAULT 0,
            joined_at    TEXT DEFAULT (datetime('now')),
            last_seen    TEXT DEFAULT (datetime('now'))
        )
    """)

    # ─── Admins ───────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            user_id   INTEGER PRIMARY KEY,
            role      TEXT DEFAULT 'support',  -- owner/manager/support/delivery
            added_by  INTEGER,
            added_at  TEXT DEFAULT (datetime('now'))
        )
    """)

    # ─── Categories ───────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            category_id  INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT UNIQUE NOT NULL,
            emoji        TEXT DEFAULT '🛍️',
            sort_order   INTEGER DEFAULT 0,
            is_active    INTEGER DEFAULT 1
        )
    """)

    # ─── Products ─────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            category_id   INTEGER,
            category      TEXT NOT NULL,
            description   TEXT,
            price         REAL NOT NULL,
            discount_price REAL,
            stock         INTEGER DEFAULT 0,
            image_url     TEXT,
            rating        REAL DEFAULT 0,
            review_count  INTEGER DEFAULT 0,
            is_active     INTEGER DEFAULT 1,
            is_featured   INTEGER DEFAULT 0,
            is_bestseller INTEGER DEFAULT 0,
            tags          TEXT,  -- comma-separated
            sold_count    INTEGER DEFAULT 0,
            created_at    TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (category_id) REFERENCES categories(category_id)
        )
    """)

    # ─── Product Images ───────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS product_images (
            image_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id  INTEGER NOT NULL,
            file_id     TEXT NOT NULL,  -- Telegram file_id
            is_primary  INTEGER DEFAULT 0,
            sort_order  INTEGER DEFAULT 0,
            FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE CASCADE
        )
    """)

    # ─── Carts ────────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS carts (
            cart_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER UNIQUE NOT NULL,
            created_at  TEXT DEFAULT (datetime('now')),
            updated_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS cart_items (
            item_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            cart_id     INTEGER NOT NULL,
            product_id  INTEGER NOT NULL,
            quantity    INTEGER DEFAULT 1,
            added_at    TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (cart_id)    REFERENCES carts(cart_id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(product_id),
            UNIQUE(cart_id, product_id)
        )
    """)

    # ─── Orders ───────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id         INTEGER NOT NULL,
            full_name       TEXT NOT NULL,
            phone           TEXT NOT NULL,
            address         TEXT NOT NULL,
            delivery_area   TEXT DEFAULT 'outside',  -- inside/outside Dhaka
            notes           TEXT,
            coupon_code     TEXT,
            discount        REAL DEFAULT 0,
            delivery_charge REAL DEFAULT 0,
            subtotal        REAL NOT NULL,
            total_price     REAL NOT NULL,
            payment_method  TEXT DEFAULT 'bkash',  -- bkash/nagad/cod
            status          TEXT DEFAULT 'pending',
            created_at      TEXT DEFAULT (datetime('now')),
            updated_at      TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            item_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id    INTEGER NOT NULL,
            product_id  INTEGER NOT NULL,
            product_name TEXT NOT NULL,  -- snapshot at order time
            quantity    INTEGER NOT NULL,
            unit_price  REAL NOT NULL,   -- snapshot at order time
            total_price REAL NOT NULL,
            FOREIGN KEY (order_id)   REFERENCES orders(order_id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)

    # ─── Payments ─────────────────────────────────────────────────────────────
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

    # ─── Coupons ──────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS coupons (
            coupon_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            code         TEXT UNIQUE NOT NULL,
            discount_pct REAL DEFAULT 0,
            discount_flat REAL DEFAULT 0,  -- flat amount discount
            min_order    REAL DEFAULT 0,   -- minimum order value
            max_uses     INTEGER DEFAULT 100,
            used_count   INTEGER DEFAULT 0,
            is_active    INTEGER DEFAULT 1,
            expires_at   TEXT,
            created_at   TEXT DEFAULT (datetime('now'))
        )
    """)

    # ─── Wishlist ─────────────────────────────────────────────────────────────
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

    # ─── Recently Viewed ──────────────────────────────────────────────────────
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

    # ─── Notifications ────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER NOT NULL,
            type        TEXT,  -- order_update / broadcast / system
            title       TEXT,
            message     TEXT,
            is_read     INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)

    # ─── Support Tickets ──────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS support_tickets (
            ticket_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            order_id     INTEGER,
            subject      TEXT,
            message      TEXT NOT NULL,
            status       TEXT DEFAULT 'open',  -- open/in_progress/resolved/closed
            assigned_to  INTEGER,
            reply        TEXT,
            created_at   TEXT DEFAULT (datetime('now')),
            updated_at   TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    """)

    # ─── Broadcasts ───────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS broadcasts (
            broadcast_id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id     INTEGER,
            message      TEXT NOT NULL,
            total_sent   INTEGER DEFAULT 0,
            total_failed INTEGER DEFAULT 0,
            sent_at      TEXT DEFAULT (datetime('now'))
        )
    """)

    # ─── Analytics ────────────────────────────────────────────────────────────
    cur.execute("""
        CREATE TABLE IF NOT EXISTS analytics (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type  TEXT NOT NULL,  -- order_placed / payment_verified / user_joined
            user_id     INTEGER,
            product_id  INTEGER,
            order_id    INTEGER,
            value       REAL DEFAULT 0,
            extra       TEXT,  -- JSON blob for additional data
            created_at  TEXT DEFAULT (datetime('now'))
        )
    """)

    # ─── Indexes ──────────────────────────────────────────────────────────────
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_orders_user     ON orders(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_orders_status   ON orders(status)",
        "CREATE INDEX IF NOT EXISTS idx_orders_created  ON orders(created_at DESC)",
        "CREATE INDEX IF NOT EXISTS idx_products_cat    ON products(category)",
        "CREATE INDEX IF NOT EXISTS idx_products_active ON products(is_active)",
        "CREATE INDEX IF NOT EXISTS idx_cart_user       ON carts(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_wishlist_user   ON wishlist(user_id)",
        "CREATE INDEX IF NOT EXISTS idx_analytics_type  ON analytics(event_type)",
    ]
    for idx in indexes:
        cur.execute(idx)

    conn.commit()
    logger.info("✅ Database initialized with full schema.")

    _seed_categories(conn)
    _seed_products(conn)
    conn.close()


def _seed_categories(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM categories")
    if cur.fetchone()[0] > 0:
        return

    categories = [
        ("Fashion", "👗", 1),
        ("Gadgets", "📱", 2),
        ("Umbrellas", "☂️", 3),
        ("Offers", "🔥", 4),
        ("New Arrivals", "✨", 5),
        ("Accessories", "👜", 6),
        ("Home & Living", "🏠", 7),
    ]
    cur.executemany(
        "INSERT INTO categories (name, emoji, sort_order) VALUES (?,?,?)",
        categories
    )
    conn.commit()
    logger.info("🌱 Categories seeded.")


def _seed_products(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM products")
    if cur.fetchone()[0] > 0:
        return

    products = [
        ("Smart Watch Pro X",     "Gadgets",    "⌚ Premium smartwatch with heart rate, sleep tracker, 7-day battery, IP67 waterproof. Android & iOS compatible. Black/Silver/Rose Gold.",                                       1499, 1299, 50, None, 4.5, 1, 1),
        ("Premium Travel Umbrella","Umbrellas",  "☂️ Double-layer windproof design. Auto open/close. UV protection, compact travel size, 10-rib structure. Lifetime warranty.",                                                    449,  349,  80, None, 4.7, 1, 0),
        ("Bluetooth Speaker X9",   "Gadgets",    "🔊 360° surround sound, 20W. IPX5 waterproof, 12-hour battery, TWS pairing, LED light ring. Festival edition available.",                                                        899,  749,  30, None, 4.3, 0, 1),
        ("Premium Cotton T-Shirt", "Fashion",    "👕 100% premium Supima cotton. S/M/L/XL/XXL. Colors: White, Black, Navy, Red, Olive. Pre-shrunk, machine washable.",                                                            349,  299, 200, None, 4.6, 0, 1),
        ("Wireless Earbuds Pro",   "Gadgets",    "🎧 Active Noise Cancellation, 30hr total with case. IPX4, touch controls, low-latency gaming mode. Crystal-clear call quality.",                                                 1299, 999,  40, None, 4.8, 1, 1),
        ("Leather Bifold Wallet",  "Accessories","👛 Genuine full-grain leather, RFID blocking, 8 card slots + 2 bill compartments. Brown & Black. Gift-boxed.",                                                                   649,  549,  75, None, 4.4, 0, 0),
        ("Folding Compact Umbrella","Umbrellas", "☂️ Ultra-compact fold, fits in any bag. Windproof 8-rib frame, UV-coated canopy. 10 colors available.",                                                                          299,  249, 120, None, 4.2, 0, 0),
        ("Summer Floral Dress",    "Fashion",    "👗 Light chiffon fabric, floral print. S/M/L/XL. Perfect for casual & semi-formal occasions. Hand wash recommended.",                                                            599,  499,  60, None, 4.5, 1, 0),
    ]

    cur.executemany("""
        INSERT INTO products
            (name, category, description, price, discount_price, stock, image_url, rating, is_featured, is_bestseller)
        VALUES (?,?,?,?,?,?,?,?,?,?)
    """, products)

    # Sample coupon
    cur.execute("""
        INSERT INTO coupons (code, discount_pct, min_order, max_uses)
        VALUES ('PICKDEAL10', 10, 500, 1000)
    """)
    cur.execute("""
        INSERT INTO coupons (code, discount_flat, min_order, max_uses)
        VALUES ('WELCOME50', 0, 300, 500)
    """)
    # Fix: update the flat one
    cur.execute("UPDATE coupons SET discount_flat=50 WHERE code='WELCOME50'")

    conn.commit()
    logger.info("🌱 Sample products and coupons seeded.")
