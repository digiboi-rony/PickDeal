"""
handlers/review_handler.py — PickDeal BD v3
Review & star rating system for delivered orders.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database.queries import get_order, get_review_by_order, create_review
from keyboards.builder import review_stars_keyboard
from utils.helpers import safe_edit, safe_answer

logger = logging.getLogger(__name__)

REVIEW_NOTE = 60   # unique conversation state


async def review_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry: show star rating for a delivered order."""
    query    = update.callback_query
    await safe_answer(query)
    order_id = int(query.data.split("_")[1])
    order    = get_order(order_id)

    if not order or order["user_id"] != update.effective_user.id:
        await query.answer("❌ অর্ডার পাওয়া যায়নি!", show_alert=True)
        return ConversationHandler.END

    if order["status"] != "delivered":
        await query.answer("⚠️ শুধুমাত্র ডেলিভারি হওয়া অর্ডারে রিভিউ দেওয়া যাবে!", show_alert=True)
        return ConversationHandler.END

    existing = get_review_by_order(order_id)
    if existing:
        stars = "⭐" * existing["rating"]
        await safe_edit(query,
            f"✅ *আপনি ইতিমধ্যে রিভিউ দিয়েছেন*\n\n"
            f"🆔 Order #{order_id}\n"
            f"⭐ রেটিং: {stars} ({existing['rating']}/5)\n"
            f"📝 মন্তব্য: {existing['note'] or '—'}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📋 আমার অর্ডার", callback_data="my_orders")
            ]]))
        return ConversationHandler.END

    context.user_data["reviewing_order_id"] = order_id
    await safe_edit(query,
        f"⭐ *রিভিউ দিন — Order #{order_id}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 আপনার অর্ডার ডেলিভারি সম্পন্ন হয়েছে!\n"
        f"আপনার অভিজ্ঞতা শেয়ার করুন:\n\n"
        f"⭐ থেকে ⭐⭐⭐⭐⭐ পর্যন্ত রেটিং দিন:",
        reply_markup=review_stars_keyboard(order_id))
    return ConversationHandler.END


async def handle_star_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: rate_<order_id>_<stars> — save rating, ask for note."""
    query = update.callback_query
    await safe_answer(query)
    parts    = query.data.split("_")
    order_id = int(parts[1])
    stars    = int(parts[2])

    context.user_data["reviewing_order_id"] = order_id
    context.user_data["reviewing_stars"]    = stars

    star_display = "⭐" * stars
    await safe_edit(query,
        f"⭐ *রেটিং: {star_display} ({stars}/5)*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 একটি সংক্ষিপ্ত মন্তব্য লিখুন:\n"
        f"_(যেমন: পণ্যের মান, ডেলিভারি, প্যাকেজিং ইত্যাদি)_\n\n"
        f"মন্তব্য না দিলে *skip* লিখুন।",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ বাতিল", callback_data="my_orders")
        ]]))
    return REVIEW_NOTE


async def handle_review_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Message handler: save the note and submit review."""
    user_id  = update.effective_user.id
    order_id = context.user_data.get("reviewing_order_id")
    stars    = context.user_data.get("reviewing_stars")

    if not order_id or not stars:
        await update.message.reply_text("⚠️ Session শেষ হয়েছে। আবার চেষ্টা করুন।")
        return ConversationHandler.END

    txt  = update.message.text.strip()
    note = None if txt.lower() in ("skip", "না", "") else txt[:300]

    create_review(order_id=order_id, user_id=user_id, rating=stars, note=note)

    context.user_data.pop("reviewing_order_id", None)
    context.user_data.pop("reviewing_stars", None)

    star_display = "⭐" * stars
    thanks = (
        "অনেক ধন্যবাদ! আপনার মতামত আমাদের আরো ভালো করতে সাহায্য করবে! 🙏"
        if stars >= 4 else
        "আপনার মতামতের জন্য ধন্যবাদ। আমরা উন্নতির চেষ্টা করব! 🙏"
    )
    await update.message.reply_text(
        f"✅ *রিভিউ সফলভাবে জমা হয়েছে!*\n\n"
        f"🆔 Order #{order_id}\n"
        f"⭐ রেটিং: {star_display} ({stars}/5)\n"
        f"📝 মন্তব্য: {note or '—'}\n\n"
        f"{thanks}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 আমার অর্ডার", callback_data="my_orders")],
            [InlineKeyboardButton("🏠 মেইন মেনু",   callback_data="main_menu")],
        ]))
    return ConversationHandler.END
