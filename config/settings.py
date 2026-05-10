"""
config/settings.py — PickDeal BD v3
All settings from environment variables. Never hardcode secrets.
"""

import os
import logging
from dotenv import load_dotenv

load_dotenv()

# ── Bot ───────────────────────────────────────────────────────────
BOT_TOKEN    = os.getenv("BOT_TOKEN", "")
BOT_NAME     = os.getenv("BOT_NAME", "PickDeal BD 🛍️")
BOT_USERNAME = os.getenv("BOT_USERNAME", "pickdealbd_bot")

# ── Admins (comma-separated Telegram user IDs) ────────────────────
ADMIN_IDS: list[int] = [
    int(x.strip()) for x in os.getenv("ADMIN_ID", "0").split(",")
    if x.strip().isdigit() and x.strip() != "0"
]

# ── Payment ───────────────────────────────────────────────────────
BKASH_NUMBER  = os.getenv("BKASH_NUMBER",  "01XXXXXXXXX")
NAGAD_NUMBER  = os.getenv("NAGAD_NUMBER",  "01XXXXXXXXX")
ROCKET_NUMBER = os.getenv("ROCKET_NUMBER", "01XXXXXXXXX")
COD_ENABLED   = os.getenv("COD_ENABLED", "true").lower() == "true"

# ── Database ──────────────────────────────────────────────────────
DB_PATH = os.getenv("DB_PATH", "pickdeal.db")

# ── Delivery defaults (overridable from DB) ───────────────────────
DEFAULT_DELIVERY_INSIDE  = int(os.getenv("DELIVERY_INSIDE_DHAKA",  "60"))
DEFAULT_DELIVERY_OUTSIDE = int(os.getenv("DELIVERY_OUTSIDE_DHAKA", "120"))

# ── Limits ────────────────────────────────────────────────────────
PRODUCTS_PER_PAGE  = 6
ADMIN_PAGE_SIZE    = 5
MAX_CART_QTY       = 10
RATE_LIMIT_SECONDS = 1

# ── Logging ───────────────────────────────────────────────────────
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE  = "logs/pickdeal.log"


def setup_logging():
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
        ],
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
