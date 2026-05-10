"""
config/settings.py
==================
Central configuration. All environment variables live here.
"""
import os
import logging
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is required in .env")

_raw = os.getenv("ADMIN_ID", "0")
ADMIN_IDS: list[int] = [int(x) for x in _raw.split(",") if x.strip().isdigit()]

BKASH_NUMBER  = os.getenv("BKASH_NUMBER",  "01XXXXXXXXX")
NAGAD_NUMBER  = os.getenv("NAGAD_NUMBER",  "01XXXXXXXXX")
COD_AVAILABLE = os.getenv("COD_AVAILABLE", "true").lower() == "true"

SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "PickDealSupport")
SUPPORT_PHONE    = os.getenv("SUPPORT_PHONE",    "01XXXXXXXXX")

DB_PATH = os.getenv("DB_PATH", "pickdeal.db")

BOT_NAME    = "PickDeal BD"
BOT_TAGLINE = "বাংলাদেশের সেরা অনলাইন শপিং 🛍️"
BOT_VERSION = "2.0.0"

PRODUCTS_PER_PAGE = 5
ORDERS_PER_PAGE   = 8

DELIVERY_CHARGE_DHAKA   = 60
DELIVERY_CHARGE_OUTSIDE = 120

LOG_LEVEL  = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"


def setup_logging():
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level    = getattr(logging, LOG_LEVEL, logging.INFO),
        format   = LOG_FORMAT,
        handlers = [
            logging.StreamHandler(),
            logging.FileHandler("logs/bot.log", encoding="utf-8"),
        ],
    )
