"""
database/db_setup.py
====================
Handles SQLite database creation and initialization.
All tables are created here with proper schema.
"""

import sqlite3
import logging
import os

logger = logging.getLogger(__name__)

# Database file path — stored in the project root
DB_PATH = os.getenv("DB_PATH", "pickdeal.db")


def get_connection():
    """
    Returns a new SQLite database connection.
    Uses row_factory so we can access columns by name (like a dict).
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name: row["column_name"]
    conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign key support
    return conn


def initialize_database():
    """
    Creates all required tables if they don't already exist.
    Safe to call multiple times (uses IF NOT EXISTS).
    """
    conn = get_connection()
    cursor = conn.cursor()

    # ─── Users Table ─────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id     INTEGER PRIMARY KEY,   -- Telegram user ID
            username    TEXT,                  -- Telegram @username (may be null)
            first_name  TEXT,                  -- Telegram first name
            last_name   TEXT,                  -- Telegram last name
            phone       TEXT,                  -- Phone number (from orders)
            is_banned   INTEGER DEFAULT 0,     -- 0 = active, 1 = banned
            referral_by INTEGER,               -- Referred by this user_id
            coupon_used TEXT,                  -- Last coupon code used
            joined_at   TEXT DEFAULT (datetime('now'))
        )
    """)

    # ─── Products Table ───────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            product_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name         TEXT NOT NULL,
            category     TEXT NOT NULL,         -- e.g. Electronics, Accessories
            description  TEXT,
            price        REAL NOT NULL,
            stock        INTEGER DEFAULT 0,
            image_url    TEXT,                  -- Telegram file_id or URL
            is_active    INTEGER DEFAULT 1      -- 1 = visible, 0 = hidden
        )
    """)

    # ─── Orders Table ────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id     INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            product_id   INTEGER NOT NULL,
            quantity     INTEGER NOT NULL DEFAULT 1,
            total_price  REAL NOT NULL,
            full_name    TEXT NOT NULL,         -- Customer name
            phone        TEXT NOT NULL,         -- Customer phone
            address      TEXT NOT NULL,         -- Delivery address
            coupon_code  TEXT,                  -- Applied coupon (if any)
            discount     REAL DEFAULT 0,        -- Discount amount
            status       TEXT DEFAULT 'pending',-- pending/confirmed/processing/shipped/delivered/cancelled
            created_at   TEXT DEFAULT (datetime('now')),
            updated_at   TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id)    REFERENCES users(user_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)

    # ─── Payments Table ───────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            payment_id      INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id        INTEGER NOT NULL,
            user_id         INTEGER NOT NULL,
            method          TEXT,               -- bKash / Nagad
            transaction_ref TEXT,               -- TRX ID (optional)
            screenshot_id   TEXT,               -- Telegram file_id of screenshot
            status          TEXT DEFAULT 'pending', -- pending/verified/rejected
            submitted_at    TEXT DEFAULT (datetime('now')),
            verified_at     TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        )
    """)

    # ─── Coupons Table ────────────────────────────────────────────────────────
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS coupons (
            coupon_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            code         TEXT UNIQUE NOT NULL,
            discount_pct REAL DEFAULT 0,        -- Percentage discount (e.g. 10 = 10%)
            max_uses     INTEGER DEFAULT 100,
            used_count   INTEGER DEFAULT 0,
            is_active    INTEGER DEFAULT 1,
            expires_at   TEXT
        )
    """)

    conn.commit()
    logger.info("✅ All database tables created/verified.")

    # Insert sample products if the table is empty
    _seed_products(conn)

    conn.close()


def _seed_products(conn):
    """
    Inserts sample products if the products table is empty.
    This gives the bot real data to work with right away.
    """
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM products")
    count = cursor.fetchone()[0]

    if count > 0:
        return  # Products already exist, skip seeding

    sample_products = [
        (
            "Smart Watch Pro",
            "Electronics",
            "⌚ Features: Heart rate monitor, sleep tracker, 7-day battery, water resistant IP67. "
            "Compatible with Android & iOS. Available in Black, Silver, Rose Gold.",
            1499.00,
            50,
            None,  # No image yet — admin can add via Telegram file_id
        ),
        (
            "Premium Umbrella",
            "Accessories",
            "☂️ Double-layer windproof umbrella. Auto open/close button. "
            "UV protection coating. Compact travel size. 10 rib structure.",
            349.00,
            100,
            None,
        ),
        (
            "Bluetooth Speaker X9",
            "Electronics",
            "🔊 360° surround sound, 20W output. IPX5 waterproof. "
            "12-hour battery life. TWS pairing supported. LED light ring.",
            899.00,
            30,
            None,
        ),
        (
            "Premium Cotton T-Shirt",
            "Clothing",
            "👕 100% premium cotton. Available in S/M/L/XL/XXL. "
            "Colors: White, Black, Navy, Red, Green. Machine washable.",
            299.00,
            200,
            None,
        ),
        (
            "Wireless Earbuds Pro",
            "Electronics",
            "🎧 Active Noise Cancellation, 30hr total battery with case. "
            "IPX4 water resistant. Touch controls. Low latency gaming mode.",
            1299.00,
            40,
            None,
        ),
        (
            "Leather Wallet",
            "Accessories",
            "👛 Genuine leather bifold wallet. RFID blocking. "
            "8 card slots + 2 bill compartments. Available in Brown & Black.",
            549.00,
            75,
            None,
        ),
    ]

    cursor.executemany(
        "INSERT INTO products (name, category, description, price, stock, image_url) VALUES (?,?,?,?,?,?)",
        sample_products,
    )

    # Insert a sample coupon
    cursor.execute(
        "INSERT INTO coupons (code, discount_pct, max_uses) VALUES (?, ?, ?)",
        ("PICKDEAL10", 10, 500),
    )

    conn.commit()
    logger.info("🌱 Sample products and coupons seeded into database.")
