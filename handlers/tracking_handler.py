"""
handlers/tracking_handler.py — PickDeal BD v3
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from database.queries import get_user_orders, get_order, get_order_items, create_ticket
from keyboards.builder import order_list_keyboard, order_detail_keyboard, support_keyboard
from utils.helpers import safe_edit, safe_answer, notify_admins
from utils.formatters import format_order_card, format_status_timeline, format_price

logger = logging.getLogger(__name__)
TICKET_MSG = 70


async def my_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    orders  = get_user_orders(user_id, limit=10)
    no_orders_text = "📋 *আমার অর্ডার*\n\nআপনি এখনো কোনো অর্ডার করেননি!"
    no_orders_kb   = InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍️ পণ্য দেখুন", callback_data="browse_categories")],
        [InlineKeyboardButton("🏠 মেইন মেনু", callback_data="main_menu")],
    ])
    if not orders:
        if update.callback_query:
            await safe_answer(update.callback_query)
            await safe_edit(update.callback_query, no_orders_text, reply_markup=no_orders_kb)
        else:
            await update.message.reply_text(no_orders_text, parse_mode="Markdown", reply_markup=no_orders_kb)
        return
    text = f"📋 *আমার অর্ডার* (সর্বশেষ {len(orders)} টি)"
    kb   = order_list_keyboard(orders)
    if update.callback_query:
        await safe_answer(update.callback_query)
        await safe_edit(update.callback_query, text, reply_markup=kb)
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)


async def view_order_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await safe_answer(query)
    order_id = int(query.data.split("_")[1])
    order    = get_order(order_id)
    if not order or order["user_id"] != update.effective_user.id:
        await query.answer("❌ অর্ডার পাওয়া যায়নি!", show_alert=True)
        return
    items      = get_order_items(order_id)
    items_text = "\n".join(f"  • {i['product_name']} × {i['quantity']} = {format_price(i['total_price'])}" for i in items)
    text = f"{format_order_card(order)}\n\n📦 *পণ্য:*\n{items_text}\n\n{format_status_timeline(order['status'])}"
    await safe_edit(query, text, reply_markup=order_detail_keyboard(order_id, order["status"]))


async def track_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if update.callback_query:
        await safe_answer(update.callback_query)
        orders = get_user_orders(user_id, limit=10)
        if not orders:
            await safe_edit(update.callback_query, "📋 আপনার কোনো অর্ডার নেই।", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 মেনু", callback_data="main_menu")]]))
            return
        await safe_edit(update.callback_query, "📋 *অর্ডার ট্র্যাক করুন:*", reply_markup=order_list_keyboard(orders))
        return
    order_id = None
    if context.args:
        try: order_id = int(context.args[0])
        except ValueError: pass
    if not order_id:
        await update.message.reply_text("🔍 `/track <order_id>` দিন\nউদাহরণ: `/track 42`", parse_mode="Markdown")
        return
    order = get_order(order_id)
    if not order or order["user_id"] != user_id:
        await update.message.reply_text("❌ অর্ডার পাওয়া যায়নি।")
        return
    items      = get_order_items(order_id)
    items_text = "\n".join(f"  • {i['product_name']} × {i['quantity']}" for i in items)
    await update.message.reply_text(
        f"{format_order_card(order)}\n\n📦 *পণ্য:*\n{items_text}\n\n{format_status_timeline(order['status'])}",
        parse_mode="Markdown", reply_markup=order_detail_keyboard(order_id, order["status"]))


async def new_ticket_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    await safe_edit(query,
        "🎫 *নতুন সাপোর্ট টিকেট*\n\nআপনার সমস্যা বা প্রশ্ন বিস্তারিত লিখুন:\n_(অর্ডার ID থাকলে উল্লেখ করুন)_",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data="support")]]))
    return TICKET_MSG


async def receive_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    message = update.message.text.strip()
    if len(message) < 5:
        await update.message.reply_text("⚠️ অনুগ্রহ করে বিস্তারিত লিখুন।")
        return TICKET_MSG
    ticket_id = create_ticket(user_id=user_id, message=message)
    await update.message.reply_text(
        f"✅ *Ticket #{ticket_id} জমা হয়েছে!*\n\nআমাদের টিম শীঘ্রই উত্তর দেবে। 🙏",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 আমার টিকেট", callback_data="my_tickets")],
            [InlineKeyboardButton("🏠 মেইন মেনু",  callback_data="main_menu")],
        ]))
    user = update.effective_user
    await notify_admins(context,
        f"🎫 *নতুন Ticket #{ticket_id}*\n"
        f"👤 {user.first_name} (@{user.username or '—'}) | ID: {user_id}\n\n"
        f"💬 {message[:400]}", parse_mode="Markdown")
    return ConversationHandler.END
