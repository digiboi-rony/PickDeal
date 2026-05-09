"""
config/settings.py
==================
Central configuration — all settings loaded from environment variables.
Never hardcode secrets here. Use .env for local development.
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

# ─── Bot Core ────────────────────────────────────────────────────────────────
BOT_TOKEN   = os.getenv("BOT_TOKEN", "")
BOT_NAME    = os.getenv("BOT_NAME", "PickDeal BD 🛍️")
BOT_USERNAME = os.getenv("BOT_USERNAME", "pickdealbd_bot")

# ─── Admin IDs ───────────────────────────────────────────────────────────────
# Comma-separated list: ADMIN_ID=123456,789012
ADMIN_IDS: list[int] = [
    int(x) for x in os.getenv("ADMIN_ID", "0").split(",")
    if x.strip().isdigit() and x.strip() != "0"
]

# ─── Payment Numbers ─────────────────────────────────────────────────────────
BKASH_NUMBER  = os.getenv("BKASH_NUMBER",  "01XXXXXXXXX")
NAGAD_NUMBER  = os.getenv("NAGAD_NUMBER",  "01XXXXXXXXX")
COD_ENABLED   = os.getenv("COD_ENABLED", "true").lower() == "true"

# ─── Database ────────────────────────────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", "pickdeal.db")

# ─── Delivery ────────────────────────────────────────────────────────────────
DELIVERY_CHARGE_INSIDE_DHAKA  = int(os.getenv("DELIVERY_INSIDE_DHAKA",  "60"))
DELIVERY_CHARGE_OUTSIDE_DHAKA = int(os.getenv("DELIVERY_OUTSIDE_DHAKA", "120"))

# ─── Limits ──────────────────────────────────────────────────────────────────
MAX_ORDER_QUANTITY      = 10
MAX_ORDERS_DISPLAY      = 10
ADMIN_PAGE_SIZE         = 5
PRODUCTS_PER_PAGE       = 8
RATE_LIMIT_SECONDS      = 1  # Min seconds between user actions

# ─── Logging ─────────────────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE  = "logs/pickdeal.log"

def setup_logging():
    """Configure structured logging for production."""
    import os
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
        ],
    )
    # Silence noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
