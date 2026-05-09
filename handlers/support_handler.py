"""
handlers/support_handler.py
============================
Customer support ticket system.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database.queries import create_ticket, get_user_tickets
from utils.helpers import safe_edit, safe_answer, notify_admins

logger = logging.getLogger(__name__)

TICKET_MESSAGE = 70


async def new_ticket_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt user to write their support message."""
    query = update.callback_query
    await safe_answer(query)
    await safe_edit(
        query,
        "🎫 *New Support Ticket*\n\n"
        "আপনার সমস্যা বা প্রশ্ন বিস্তারিত লিখুন:\n\n"
        "_(অর্ডার ID থাকলে উল্লেখ করুন)_",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="support")
        ]])
    )
    return TICKET_MESSAGE


async def receive_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save ticket and notify admins."""
    user_id = update.effective_user.id
    message = update.message.text.strip()

    if len(message) < 5:
        await update.message.reply_text("⚠️ অনুগ্রহ করে বিস্তারিত লিখুন।")
        return TICKET_MESSAGE

    ticket_id = create_ticket(user_id=user_id, message=message)

    await update.message.reply_text(
        f"✅ *Support Ticket #{ticket_id} জমা হয়েছে!*\n\n"
        f"আমাদের টিম শীঘ্রই আপনার সাথে যোগাযোগ করবে।\n"
        f"সাধারণত ১–৩ ঘণ্টার মধ্যে উত্তর দেওয়া হয়। 🙏",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 My Tickets", callback_data="my_tickets")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
        ])
    )

    user = update.effective_user
    name = user.first_name or "Unknown"
    username = f"@{user.username}" if user.username else "—"

    await notify_admins(
        update,  # context not available here, workaround via bot
        f"🎫 *New Support Ticket #{ticket_id}*\n"
        f"👤 {name} ({username}) | ID: {user_id}\n\n"
        f"💬 {message[:400]}",
        parse_mode="Markdown"
    )
    return ConversationHandler.END


async def my_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's own support tickets."""
    query = update.callback_query
    await safe_answer(query)
    user_id = update.effective_user.id
    tickets = get_user_tickets(user_id)

    if not tickets:
        await safe_edit(
            query,
            "🎫 *My Support Tickets*\n\nআপনার কোনো টিকেট নেই।",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🆕 New Ticket", callback_data="new_ticket")],
                [InlineKeyboardButton("🏠 Main Menu",  callback_data="main_menu")],
            ])
        )
        return

    text_lines = ["🎫 *My Support Tickets*\n"]
    for t in tickets:
        status_map = {"open": "🔴 Open", "in_progress": "🟡 In Progress",
                      "resolved": "🟢 Resolved", "closed": "⚫ Closed"}
        st = status_map.get(t["status"], t["status"])
        text_lines.append(
            f"━━━━━━━━━━\n"
            f"🎫 Ticket #{t['ticket_id']} | {st}\n"
            f"📅 {str(t['created_at'])[:16]}\n"
            f"💬 {t['message'][:80]}...\n"
        )
        if t.get("reply"):
            text_lines.append(f"📩 *Reply:* {t['reply'][:100]}")

    await safe_edit(
        query,
        "\n".join(text_lines),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🆕 New Ticket", callback_data="new_ticket")],
            [InlineKeyboardButton("🏠 Main Menu",  callback_data="main_menu")],
        ])
    )
