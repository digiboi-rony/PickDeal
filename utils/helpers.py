"""
utils/helpers.py
================
Shared utility functions used across all handlers.
"""

import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# ─── Admin Configuration ─────────────────────────────────────────────────────
# ADMIN_ID: Your Telegram numeric user ID (not username)
# Get it by messaging @userinfobot on Telegram
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_ID", "0").split(",") if x.strip().isdigit()]

# Payment account numbers
BKASH_NUMBER  = os.getenv("BKASH_NUMBER",  "01XXXXXXXXX")
NAGAD_NUMBER  = os.getenv("NAGAD_NUMBER",   "01XXXXXXXXX")

# Bot display name
BOT_NAME = "PickDeal BD 🛍️"


def is_admin(user_id: int) -> bool:
    """Check if a user is an admin."""
    return user_id in ADMIN_IDS


def format_price(amount: float) -> str:
    """Format a price with Bangladeshi Taka symbol."""
    return f"৳{amount:,.0f}"


def format_order_status(status: str) -> str:
    """Convert status code to a human-readable emoji string."""
    status_map = {
        "pending":    "🕐 Pending",
        "confirmed":  "✅ Payment Confirmed",
        "processing": "⚙️ Processing",
        "shipped":    "🚚 Shipped",
        "delivered":  "📦 Delivered",
        "cancelled":  "❌ Cancelled",
    }
    return status_map.get(status, f"❓ {status.title()}")


def format_order_card(order) -> str:
    """
    Format a single order as a nicely readable message card.
    `order` should be a sqlite3.Row with order + product columns.
    """
    status_emoji = format_order_status(order["status"])
    price = format_price(order["total_price"])
    created = order["created_at"][:16]  # Trim seconds

    return (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *Order #{order['order_id']}*\n"
        f"📦 *Product:* {order['product_name']}\n"
        f"🔢 *Qty:* {order['quantity']}\n"
        f"💰 *Total:* {price}\n"
        f"📍 *Address:* {order['address']}\n"
        f"📅 *Date:* {created}\n"
        f"🚦 *Status:* {status_emoji}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )


def format_product_card(product) -> str:
    """Format a product as a message card."""
    price = format_price(product["price"])
    stock_text = "✅ In Stock" if product["stock"] > 0 else "❌ Out of Stock"
    return (
        f"🛍️ *{product['name']}*\n\n"
        f"📝 {product['description']}\n\n"
        f"💰 *Price:* {price}\n"
        f"📦 *Stock:* {stock_text} ({product['stock']} left)\n"
        f"🏷️ *Category:* {product['category']}"
    )


def format_datetime(dt_str: str) -> str:
    """Format a datetime string for display."""
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%d %b %Y, %I:%M %p")
    except Exception:
        return dt_str


# ─── Category Emojis ─────────────────────────────────────────────────────────
CATEGORY_EMOJI = {
    "Electronics":  "⚡",
    "Accessories":  "👜",
    "Clothing":     "👕",
    "Home & Living":"🏠",
    "Beauty":       "💄",
    "Sports":       "🏋️",
    "Books":        "📚",
    "Toys":         "🧸",
}

def get_category_emoji(category: str) -> str:
    """Return the emoji for a product category."""
    return CATEGORY_EMOJI.get(category, "🛍️")


# ─── Order Status Flow ────────────────────────────────────────────────────────
# Defines valid next statuses for each current status
STATUS_FLOW = {
    "pending":    ["confirmed", "cancelled"],
    "confirmed":  ["processing", "cancelled"],
    "processing": ["shipped"],
    "shipped":    ["delivered"],
    "delivered":  [],
    "cancelled":  [],
}

STATUS_LABELS = {
    "confirmed":  "✅ Confirm Payment",
    "processing": "⚙️ Mark Processing",
    "shipped":    "🚚 Mark Shipped",
    "delivered":  "📦 Mark Delivered",
    "cancelled":  "❌ Cancel Order",
}
