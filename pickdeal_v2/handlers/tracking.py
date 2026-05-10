"""handlers/tracking.py — order tracking and my orders"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import models.order as order_model
from keyboards.order_kb import my_orders_kb, order_detail_kb
from utils.formatters import order_card, order_status_timeline

logger = logging.getLogger(__name__)


async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's orders. Callback: my_orders"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    orders = order_model.get_user_orders(user_id)
    if not orders:
        await query.edit_message_text(
            "📋 *আমার অর্ডার*\n\nএখনো কোনো অর্ডার নেই।\nশপিং শুরু করুন! 🛍️",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🛍️ পণ্য দেখুন", callback_data="browse"),
                InlineKeyboardButton("⬅️ মেনু",        callback_data="main_menu"),
            ]])
        )
        return

    await query.edit_message_text(
        f"📋 *আমার অর্ডার* ({len(orders)}টি)\n\nঅর্ডার বেছে নিন:",
        parse_mode="Markdown",
        reply_markup=my_orders_kb(orders),
    )


async def order_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show single order detail. Callback: order_detail_<id>"""
    query    = update.callback_query
    await query.answer()
    user_id  = update.effective_user.id
    order_id = int(query.data.split("_")[2])

    order = order_model.get(order_id)
    if not order or order["user_id"] != user_id:
        await query.answer("❌ অর্ডার পাওয়া যায়নি!", show_alert=True)
        return

    items    = order_model.get_items(order_id)
    text     = order_card(order, items)
    timeline = order_status_timeline(order["status"])

    await query.edit_message_text(
        f"{text}\n\n{timeline}",
        parse_mode="Markdown",
        reply_markup=order_detail_kb(order_id, order["status"]),
    )


async def track_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/track <order_id> command handler."""
    user_id = update.effective_user.id

    if not context.args:
        await update.message.reply_text(
            "🔍 *অর্ডার ট্র্যাক করুন*\n\n"
            "কমান্ড: `/track <অর্ডার নম্বর>`\n"
            "_(যেমন: /track 42)_",
            parse_mode="Markdown"
        )
        return

    try:
        order_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ সঠিক অর্ডার নম্বর দিন।")
        return

    order = order_model.get(order_id)
    if not order or order["user_id"] != user_id:
        await update.message.reply_text("❌ অর্ডার পাওয়া যায়নি বা এটি আপনার নয়।")
        return

    items    = order_model.get_items(order_id)
    text     = order_card(order, items)
    timeline = order_status_timeline(order["status"])

    await update.message.reply_text(
        f"{text}\n\n{timeline}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📋 সব অর্ডার", callback_data="my_orders"),
            InlineKeyboardButton("⬅️ মেনু",      callback_data="main_menu"),
        ]])
    )
