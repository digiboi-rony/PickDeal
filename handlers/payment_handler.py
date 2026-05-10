"""
handlers/payment_handler.py — PickDeal BD v3
Dynamic payment methods from DB. Screenshot → admin verification.
FIX: payment method loaded from payment_methods table, not hardcoded.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database.queries import (
    get_order, get_payment_methods, get_payment_method,
    save_payment, update_order_status,
)
from keyboards.builder import payment_methods_keyboard
from utils.helpers import safe_edit, safe_answer, notify_admins_photo, notify_admins
from utils.formatters import format_price
from config.settings import ADMIN_IDS

logger = logging.getLogger(__name__)
WAITING_SCREENSHOT = 20


async def select_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show dynamic payment method list for an order."""
    query    = update.callback_query
    await safe_answer(query)
    order_id = int(query.data.split("_")[1])
    order    = get_order(order_id)

    if not order or order["user_id"] != update.effective_user.id:
        await query.answer("❌ অর্ডার পাওয়া যায়নি!", show_alert=True)
        return ConversationHandler.END

    methods = get_payment_methods(active_only=True)
    if not methods:
        await query.answer("⚠️ কোনো পেমেন্ট পদ্ধতি সক্রিয় নেই!", show_alert=True)
        return ConversationHandler.END

    context.user_data["paying_order_id"] = order_id

    await safe_edit(query,
        f"💳 *পেমেন্ট পদ্ধতি বেছে নিন*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 Order: *#{order_id}*\n"
        f"💰 পরিমাণ: *{format_price(order['total_price'])}*\n"
        f"━━━━━━━━━━━━━━━━━━━━",
        reply_markup=payment_methods_keyboard(methods, order_id))
    return ConversationHandler.END


async def show_payment_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback: pay_<order_id>_<method_id>
    Loads payment method from DB and shows instructions.
    """
    query  = update.callback_query
    await safe_answer(query)
    parts  = query.data.split("_")
    order_id  = int(parts[1])
    method_id = int(parts[2])

    order  = get_order(order_id)
    method = get_payment_method(method_id)

    if not order or not method:
        await query.answer("❌ তথ্য পাওয়া যায়নি!", show_alert=True)
        return ConversationHandler.END

    if order["user_id"] != update.effective_user.id:
        await query.answer("❌ Unauthorized!", show_alert=True)
        return ConversationHandler.END

    context.user_data["paying_order_id"]  = order_id
    context.user_data["paying_method_id"] = method_id
    context.user_data["paying_method"]    = method["name"]

    # COD — no screenshot needed
    if method["is_cod"]:
        update_order_status(order_id, "confirmed")
        await safe_edit(query,
            f"✅ *ক্যাশ অন ডেলিভারি নিশ্চিত!*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 Order: *#{order_id}*\n"
            f"💵 পরিমাণ: *{format_price(order['total_price'])}* (পণ্য পাওয়ার সময় দিন)\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"আমাদের ডেলিভারি টিম শীঘ্রই যোগাযোগ করবে! 🚚",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 আমার অর্ডার", callback_data="my_orders")],
                [InlineKeyboardButton("🏠 মেইন মেনু",   callback_data="main_menu")],
            ]))
        await notify_admins(context,
            f"💵 *COD অর্ডার*\n🆔 #{order_id}\n"
            f"👤 {order['full_name']}\n📞 {order['phone']}\n"
            f"💰 {format_price(order['total_price'])}",
            parse_mode="Markdown")
        return ConversationHandler.END

    # Digital payment — show instructions, wait for screenshot
    number = method["number"] or "—"
    await safe_edit(query,
        f"{method['emoji']} *{method['name']} পেমেন্ট*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 Order: *#{order_id}*\n"
        f"💰 পরিমাণ: *{format_price(order['total_price'])}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📱 *{method['name']} নম্বর:*\n"
        f"`{number}`\n\n"
        f"🔄 *ধরন:* Send Money\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ *গুরুত্বপূর্ণ:*\n"
        f"• ঠিক *{format_price(order['total_price'])}* পাঠান\n"
        f"• 'Send Money' ব্যবহার করুন\n"
        f"• পেমেন্টের স্ক্রিনশট পাঠান\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📸 *এখন স্ক্রিনশট পাঠান:*",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ বাতিল", callback_data="my_orders")
        ]]))
    return WAITING_SCREENSHOT


async def receive_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive payment screenshot, forward to admins."""
    user     = update.effective_user
    order_id = context.user_data.get("paying_order_id")
    method   = context.user_data.get("paying_method", "—")

    if not order_id:
        await update.message.reply_text("⚠️ Session শেষ হয়েছে। My Orders থেকে আবার চেষ্টা করুন।")
        return ConversationHandler.END

    order = get_order(order_id)
    if not order:
        await update.message.reply_text("❌ অর্ডার পাওয়া যায়নি।")
        return ConversationHandler.END

    if not update.message.photo:
        await update.message.reply_text("📸 শুধু ছবি (স্ক্রিনশট) পাঠান।")
        return WAITING_SCREENSHOT

    file_id = update.message.photo[-1].file_id
    save_payment(
        order_id=order_id, user_id=user.id, method=method,
        screenshot_id=file_id, amount=order["total_price"],
        trx_ref=update.message.caption or None,
    )

    # Forward screenshot to all admins
    admin_caption = (
        f"💳 *পেমেন্ট স্ক্রিনশট*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 Order: *#{order_id}*\n"
        f"👤 Customer: {order['full_name']}\n"
        f"📞 Phone: {order['phone']}\n"
        f"💰 Amount: {format_price(order['total_price'])}\n"
        f"💳 Method: {method}\n"
        f"👤 User ID: `{user.id}`"
    )
    admin_buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ পেমেন্ট নিশ্চিত", callback_data=f"admupd_{order_id}_confirmed")],
        [InlineKeyboardButton("❌ প্রত্যাখ্যান",    callback_data=f"admupd_{order_id}_cancelled")],
    ])

    await notify_admins_photo(
        context, photo=file_id,
        caption=admin_caption, parse_mode="Markdown",
        reply_markup=admin_buttons
    )

    await update.message.reply_text(
        f"✅ *পেমেন্ট স্ক্রিনশট পাওয়া গেছে!*\n\n"
        f"🆔 Order: *#{order_id}*\n\n"
        f"আমাদের টিম ১–৩ ঘণ্টার মধ্যে ভেরিফাই করবে। নিশ্চিত হলে জানানো হবে! 🎉",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 আমার অর্ডার", callback_data="my_orders")],
            [InlineKeyboardButton("🏠 মেইন মেনু",   callback_data="main_menu")],
        ]))

    context.user_data.pop("paying_order_id", None)
    context.user_data.pop("paying_method",   None)
    context.user_data.pop("paying_method_id",None)
    return ConversationHandler.END
