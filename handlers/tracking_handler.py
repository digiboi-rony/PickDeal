"""
handlers/tracking_handler.py
=============================
Handles order tracking and 'My Orders' section.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.queries import get_user_orders, get_order
from utils.helpers import format_order_card, format_order_status

logger = logging.getLogger(__name__)

# Delivery status timeline for display
STATUS_TIMELINE = [
    ("pending",    "🕐", "Order Placed"),
    ("confirmed",  "✅", "Payment Confirmed"),
    ("processing", "⚙️", "Being Processed"),
    ("shipped",    "🚚", "Shipped"),
    ("delivered",  "📦", "Delivered"),
]


def build_status_timeline(current_status: str) -> str:
    """Build a visual delivery progress timeline."""
    lines = ["📍 *Delivery Progress:*\n"]
    reached = False

    for status_key, emoji, label in STATUS_TIMELINE:
        if status_key == current_status:
            lines.append(f"➡️ *{emoji} {label}* ← You are here")
            reached = True
        elif not reached:
            lines.append(f"✔️ {emoji} {label}")
        else:
            lines.append(f"⬜ {emoji} {label}")

        if status_key == "cancelled":
            break

    if current_status == "cancelled":
        lines = ["❌ *Order Cancelled*\n\nThis order has been cancelled."]

    return "\n".join(lines)


async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show the last 10 orders for the current user.
    Can be triggered by /orders command or 'my_orders' callback.
    """
    user_id = update.effective_user.id
    orders = get_user_orders(user_id)

    if not orders:
        no_orders_text = (
            "📋 *My Orders*\n\n"
            "You haven't placed any orders yet!\n\n"
            "Start shopping to see your orders here 🛍️"
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🛍️ Browse Products", callback_data="browse_products"),
            InlineKeyboardButton("⬅️ Menu",            callback_data="main_menu"),
        ]])

        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                no_orders_text, parse_mode="Markdown", reply_markup=keyboard
            )
        else:
            await update.message.reply_text(
                no_orders_text, parse_mode="Markdown", reply_markup=keyboard
            )
        return

    # Build order list with inline buttons
    text = f"📋 *Your Orders* (Last {len(orders)})\n\n"
    buttons = []

    for order in orders:
        status = format_order_status(order["status"])
        label = f"#{order['order_id']} | {order['product_name'][:20]} | {status}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"view_order_{order['order_id']}")])

    buttons.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")])

    text += "Tap an order to see details and track delivery:"

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    else:
        await update.message.reply_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons)
        )


async def track_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Track a specific order.
    Can be triggered by /track <order_id> or the 'track_order' callback button.
    """
    user_id = update.effective_user.id

    # Try to get order_id from command args (/track 123)
    order_id = None
    if update.message and context.args:
        try:
            order_id = int(context.args[0])
        except (ValueError, IndexError):
            pass

    # If triggered from callback (track_order button), ask for order ID
    if update.callback_query and not order_id:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "🔍 *Track Your Order*\n\n"
            "Please use the command:\n"
            "`/track <order_id>`\n\n"
            "_Example: /track 42_",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📋 My Orders", callback_data="my_orders"),
                InlineKeyboardButton("⬅️ Menu",      callback_data="main_menu"),
            ]])
        )
        return

    if not order_id:
        await update.message.reply_text(
            "🔍 *Track Your Order*\n\n"
            "Please provide your order ID:\n"
            "`/track <order_id>`\n\n"
            "_Example: /track 42_",
            parse_mode="Markdown",
        )
        return

    order = get_order(order_id)

    if not order:
        await update.message.reply_text(f"❌ Order #{order_id} not found.")
        return

    # Security: only allow user to track their own orders
    if order["user_id"] != user_id:
        await update.message.reply_text("❌ You can only track your own orders.")
        return

    order_card = format_order_card(order)
    timeline = build_status_timeline(order["status"])

    full_text = f"{order_card}\n\n{timeline}"

    buttons = []
    # Show Pay button if order is pending and not paid yet
    if order["status"] == "pending":
        buttons.append([InlineKeyboardButton("💳 Pay Now", callback_data=f"pay_order_{order_id}")])

    buttons.append([
        InlineKeyboardButton("📋 All Orders", callback_data="my_orders"),
        InlineKeyboardButton("⬅️ Menu",       callback_data="main_menu"),
    ])

    await update.message.reply_text(
        full_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
