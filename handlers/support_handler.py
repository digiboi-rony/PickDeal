"""
handlers/support_handler.py
============================
Handles the customer support section.
"""

import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

SUPPORT_USERNAME = os.getenv("SUPPORT_USERNAME", "PickDealSupport")
SUPPORT_PHONE    = os.getenv("SUPPORT_PHONE", "01XXXXXXXXX")


async def customer_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show customer support options."""
    query = update.callback_query
    await query.answer()

    support_text = (
        f"💬 *Customer Support*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"We're here to help! 😊\n\n"
        f"📞 *Phone/WhatsApp:*\n"
        f"`{SUPPORT_PHONE}`\n\n"
        f"💬 *Telegram:*\n"
        f"@{SUPPORT_USERNAME}\n\n"
        f"🕐 *Support Hours:*\n"
        f"Saturday–Thursday\n"
        f"10:00 AM – 8:00 PM\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"❓ *Common Questions:*"
    )

    faq_buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 Where is my order?",       callback_data="track_order")],
        [InlineKeyboardButton("💳 Payment not confirmed?",   callback_data="faq_payment")],
        [InlineKeyboardButton("🔄 Return / Refund policy",  callback_data="faq_return")],
        [InlineKeyboardButton("🚚 Delivery time?",           callback_data="faq_delivery")],
        [InlineKeyboardButton("⬅️ Back to Menu",             callback_data="main_menu")],
    ])

    await query.edit_message_text(
        support_text,
        parse_mode="Markdown",
        reply_markup=faq_buttons,
    )
