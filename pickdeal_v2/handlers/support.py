"""handlers/support.py — customer support and ticket system"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database.connection import get_conn
from config.settings import SUPPORT_USERNAME, SUPPORT_PHONE

logger = logging.getLogger(__name__)
TICKET_MSG = 300


async def support_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show support options."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        f"💬 *কাস্টমার সাপোর্ট*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📞 ফোন/WhatsApp: `{SUPPORT_PHONE}`\n"
        f"💬 Telegram: @{SUPPORT_USERNAME}\n"
        f"🕐 সময়: শনি–বৃহস্পতি, সকাল ১০টা – রাত ৮টা\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"❓ *সাধারণ প্রশ্ন:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 অর্ডার কোথায়?",      callback_data="my_orders")],
            [InlineKeyboardButton("💳 পেমেন্ট নিশ্চিত হয়নি?", callback_data="faq_payment")],
            [InlineKeyboardButton("🔄 রিটার্ন/রিফান্ড",    callback_data="faq_return")],
            [InlineKeyboardButton("✉️ টিকিট পাঠান",         callback_data="send_ticket")],
            [InlineKeyboardButton("⬅️ মেনু",               callback_data="main_menu")],
        ])
    )


async def faq_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "💳 *পেমেন্ট নিশ্চিত না হলে:*\n\n"
        "১. স্ক্রিনশট সাবমিট করেছেন কিনা দেখুন\n"
        "২. ১-৩ ঘণ্টা অপেক্ষা করুন\n"
        "৩. এখনো না হলে সাপোর্টে যোগাযোগ করুন\n\n"
        f"📞 {SUPPORT_PHONE}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ সাপোর্ট", callback_data="support")
        ]])
    )


async def faq_return(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🔄 *রিটার্ন ও রিফান্ড নীতি:*\n\n"
        "• পণ্য পাওয়ার ৩ দিনের মধ্যে রিটার্ন করা যাবে\n"
        "• পণ্য ত্রুটিপূর্ণ হলে বিনামূল্যে প্রতিস্থাপন\n"
        "• রিফান্ড ৫-৭ কার্যদিবসে প্রসেস হবে\n\n"
        f"সাপোর্ট: {SUPPORT_PHONE}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ সাপোর্ট", callback_data="support")
        ]])
    )


async def start_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask user to type their support message."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "✉️ *সাপোর্ট টিকিট পাঠান*\n\n"
        "আপনার সমস্যা বিস্তারিত লিখুন:\n"
        "_(অর্ডার নম্বর, সমস্যার বিবরণ)_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ বাতিল", callback_data="support")
        ]])
    )
    return TICKET_MSG


async def save_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message.text.strip()

    conn = get_conn()
    conn.execute(
        "INSERT INTO support_tickets(user_id,message) VALUES(?,?)", (user_id, message)
    )
    conn.commit()

    await update.message.reply_text(
        "✅ *টিকিট পাঠানো হয়েছে!*\n\n"
        "আমরা শীঘ্রই যোগাযোগ করব।\n"
        f"সরাসরি: @{SUPPORT_USERNAME}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ মেনু", callback_data="main_menu")
        ]])
    )
    return ConversationHandler.END
