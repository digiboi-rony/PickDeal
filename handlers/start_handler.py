"""
handlers/start_handler.py
=========================
Handles the /start command and the main menu.
This is the first thing customers see when they open the bot.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.queries import upsert_user
from utils.helpers import BOT_NAME

logger = logging.getLogger(__name__)

# ─── Welcome Message ──────────────────────────────────────────────────────────
WELCOME_TEXT = """
🎉 *Welcome to {bot_name}!*

Bangladesh's #1 online shopping destination.
Quality products, fast delivery across Bangladesh! 🇧🇩

━━━━━━━━━━━━━━━━━━━━
📦 *What can I do?*
• Browse & order products
• Track your delivery
• Pay via bKash / Nagad
• Get customer support
━━━━━━━━━━━━━━━━━━━━

Tap a button below to get started! 👇
""".strip()


def build_main_menu_keyboard():
    """Build the main menu inline keyboard."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🛍️ Browse Products",  callback_data="browse_products"),
        ],
        [
            InlineKeyboardButton("📋 My Orders",        callback_data="my_orders"),
            InlineKeyboardButton("🔍 Track Order",      callback_data="track_order"),
        ],
        [
            InlineKeyboardButton("🎫 Use Coupon",       callback_data="use_coupon"),
            InlineKeyboardButton("💬 Support",          callback_data="support"),
        ],
    ])


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start command handler.
    Registers the user and shows the main menu.
    """
    user = update.effective_user

    # Save/update user in database
    upsert_user(
        user_id    = user.id,
        username   = user.username or "",
        first_name = user.first_name or "",
        last_name  = user.last_name or "",
    )

    logger.info(f"User {user.id} ({user.first_name}) started the bot.")

    # Check for referral code in /start payload (e.g., /start ref_12345)
    if context.args:
        payload = context.args[0]
        if payload.startswith("ref_"):
            referrer_id = payload[4:]
            context.user_data["referral_by"] = referrer_id

    welcome_text = WELCOME_TEXT.format(bot_name=BOT_NAME)

    await update.message.reply_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=build_main_menu_keyboard(),
    )


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback handler to return to main menu.
    Triggered by the 'main_menu' callback button.
    """
    query = update.callback_query
    await query.answer()

    welcome_text = WELCOME_TEXT.format(bot_name=BOT_NAME)

    await query.edit_message_text(
        welcome_text,
        parse_mode="Markdown",
        reply_markup=build_main_menu_keyboard(),
    )
