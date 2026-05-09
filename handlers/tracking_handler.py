"""
handlers/tracking_handler.py
=============================
My Orders list and individual order detail with status timeline.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.queries import get_user_orders, get_order, get_order_items
from keyboards.builder import order_list_keyboard, order_detail_keyboard
from utils.helpers import safe_edit, safe_answer
from utils.formatters import format_order_card, format_status_timeline, format_price

logger = logging.getLogger(__name__)


async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show last 10 orders for the user."""
    user_id = update.effective_user.id
    orders = get_user_orders(user_id, limit=10)

    text_no_orders = (
        "📋 *আমার অর্ডার*\n\n"
        "আপনি এখনো কোনো অর্ডার করেননি!\n\n"
        "🛍️ আজই শপিং শুরু করুন!"
    )
    kb_no = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍️ Browse Products", callback_data="browse_products")],
        [InlineKeyboardButton("🏠 Main Menu",       callback_data="main_menu")],
    ])

    if not orders:
        if update.callback_query:
            await safe_answer(update.callback_query)
            await safe_edit(update.callback_query, text_no_orders, reply_markup=kb_no)
        else:
            await update.message.reply_text(text_no_orders, parse_mode="Markdown", reply_markup=kb_no)
        return

    text = f"📋 *আমার অর্ডার* (সর্বশেষ {len(orders)}টি)\n\nবিস্তারিত দেখতে অর্ডারে ক্লিক করুন:"
    kb = order_list_keyboard(orders)

    if update.callback_query:
        await safe_answer(update.callback_query)
        await safe_edit(update.callback_query, text, reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)


async def view_order_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show full detail of a specific order."""
    query = update.callback_query
    await safe_answer(query)
    user_id = update.effective_user.id

    order_id = int(query.data.split("_")[1])
    order = get_order(order_id)

    if not order:
        await query.answer("❌ Order পাওয়া যায়নি!", show_alert=True)
        return

    if order["user_id"] != user_id:
        await query.answer("❌ এটি আপনার অর্ডার নয়!", show_alert=True)
        return

    items = get_order_items(order_id)
    items_text = "\n".join(
        f"  • {i['product_name']} × {i['quantity']} = {format_price(i['total_price'])}"
        for i in items
    )

    order_text = format_order_card(order)
    timeline = format_status_timeline(order["status"])

    full_text = (
        f"{order_text}\n\n"
        f"📦 *Order Items:*\n{items_text}\n\n"
        f"{timeline}"
    )

    await safe_edit(
        query,
        full_text,
        reply_markup=order_detail_keyboard(order_id, order["status"])
    )


async def track_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /track <order_id> command OR track_order callback.
    Callback just redirects to My Orders list.
    """
    user_id = update.effective_user.id

    # Callback: just show my orders list
    if update.callback_query:
        await safe_answer(update.callback_query)
        orders = get_user_orders(user_id, limit=10)
        if not orders:
            await safe_edit(
                update.callback_query,
                "📋 আপনার কোনো অর্ডার নেই।",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🛍️ Shop Now", callback_data="browse_products"),
                    InlineKeyboardButton("🏠 Menu",     callback_data="main_menu"),
                ]])
            )
            return
        await safe_edit(
            update.callback_query,
            "📋 *Track Order*\n\nঅর্ডার ট্র্যাক করতে নিচ থেকে বেছে নিন:",
            reply_markup=order_list_keyboard(orders)
        )
        return

    # /track command
    order_id = None
    if context.args:
        try:
            order_id = int(context.args[0])
        except ValueError:
            pass

    if not order_id:
        await update.message.reply_text(
            "🔍 *Order Track করুন*\n\n"
            "কমান্ড: `/track <order_id>`\n"
            "উদাহরণ: `/track 42`",
            parse_mode="Markdown",
        )
        return

    order = get_order(order_id)

    if not order:
        await update.message.reply_text(f"❌ Order #{order_id} পাওয়া যায়নি।")
        return

    if order["user_id"] != user_id:
        await update.message.reply_text("❌ এটি আপনার অর্ডার নয়।")
        return

    items = get_order_items(order_id)
    items_text = "\n".join(
        f"  • {i['product_name']} × {i['quantity']} = {format_price(i['total_price'])}"
        for i in items
    )

    full_text = (
        f"{format_order_card(order)}\n\n"
        f"📦 *Items:*\n{items_text}\n\n"
        f"{format_status_timeline(order['status'])}"
    )

    await update.message.reply_text(
        full_text,
        parse_mode="Markdown",
        reply_markup=order_detail_keyboard(order_id, order["status"])
    )
