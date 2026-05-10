"""handlers/payment.py — payment method selection + screenshot upload"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

import models.payment as payment_model
import models.order as order_model
from services.notification import notify_admins
from keyboards.admin_kb import order_action_kb
from utils.formatters import taka
from config.settings import BKASH_NUMBER, NAGAD_NUMBER, ADMIN_IDS

logger = logging.getLogger(__name__)

WAITING_SCREENSHOT = 200


async def choose_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show payment method selection.
    Callback pattern: pay_<order_id>_<method> or choose_payment_<order_id>
    """
    query = update.callback_query
    await query.answer()

    parts = query.data.split("_")

    # If coming from choose_payment_<order_id>
    if parts[0] == "choose":
        order_id = int(parts[2])
        from keyboards.order_kb import payment_method_kb
        await query.edit_message_text(
            f"💳 *পেমেন্ট পদ্ধতি বেছে নিন:*\n🆔 অর্ডার: #{order_id}",
            parse_mode="Markdown",
            reply_markup=payment_method_kb(order_id),
        )
        return

    # pay_<order_id>_<method>
    order_id = int(parts[1])
    method   = parts[2]  # bkash / nagad / cod

    order = order_model.get(order_id)
    if not order or order["user_id"] != update.effective_user.id:
        await query.answer("❌ অর্ডার পাওয়া যায়নি!", show_alert=True)
        return

    context.user_data["paying_order_id"] = order_id
    context.user_data["paying_method"]   = method

    # COD: no screenshot needed
    if method == "cod":
        await _handle_cod(query, order_id, order)
        return

    # bKash / Nagad: show instructions + ask for screenshot
    number = BKASH_NUMBER if method == "bkash" else NAGAD_NUMBER
    name   = "bKash" if method == "bkash" else "Nagad"

    text = (
        f"📱 *{name} পেমেন্ট নির্দেশনা*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 অর্ডার: #{order_id}\n"
        f"💰 পরিমাণ: *{taka(order['total'])}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📲 *Send Money করুন:*\n"
        f"নম্বর: `{number}`\n"
        f"ধরন: Send Money\n\n"
        f"⚠️ *গুরুত্বপূর্ণ:*\n"
        f"• ঠিক {taka(order['total'])} পাঠান\n"
        f"• 'Send Money' ব্যবহার করুন\n"
        f"• পেমেন্টের পর স্ক্রিনশট পাঠান\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📸 *এখন স্ক্রিনশট পাঠান:*"
    )
    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ বাতিল", callback_data="main_menu")
        ]])
    )
    return WAITING_SCREENSHOT


async def receive_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive payment screenshot, save it, notify admins."""
    user_id  = update.effective_user.id
    order_id = context.user_data.get("paying_order_id")
    method   = context.user_data.get("paying_method", "bkash")

    if not order_id:
        await update.message.reply_text("⚠️ সেশন শেষ হয়ে গেছে। /start দিন।")
        return ConversationHandler.END

    order = order_model.get(order_id)
    if not order:
        await update.message.reply_text("❌ অর্ডার পাওয়া যায়নি।")
        return ConversationHandler.END

    photo   = update.message.photo[-1]
    file_id = photo.file_id
    trx_ref = update.message.caption or None

    payment_model.save(order_id, user_id, method, file_id, trx_ref)

    # ─── Notify admins with screenshot ────────────────────────────────────────
    caption = (
        f"📸 *নতুন পেমেন্ট স্ক্রিনশট!*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 অর্ডার: #{order_id}\n"
        f"👤 গ্রাহক: {order['full_name']}\n"
        f"📞 ফোন: {order['phone']}\n"
        f"💳 পদ্ধতি: {method.upper()}\n"
        f"💰 পরিমাণ: {taka(order['total'])}\n"
        f"🆔 TG ID: {user_id}"
    )
    kb = order_action_kb(order_id, order["status"])

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_photo(
                chat_id      = admin_id,
                photo        = file_id,
                caption      = caption,
                parse_mode   = "Markdown",
                reply_markup = kb,
            )
        except Exception as e:
            logger.error(f"Admin screenshot forward failed: {e}")

    # ─── Confirm to customer ──────────────────────────────────────────────────
    context.user_data.pop("paying_order_id", None)
    context.user_data.pop("paying_method", None)

    await update.message.reply_text(
        f"✅ *পেমেন্ট স্ক্রিনশট পাওয়া গেছে!*\n\n"
        f"🆔 অর্ডার: #{order_id}\n\n"
        f"আমরা যাচাই করে ১-৩ ঘণ্টার মধ্যে কনফার্ম করব।\n"
        f"নোটিফিকেশন পাবেন! 🔔",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 আমার অর্ডার", callback_data="my_orders")],
            [InlineKeyboardButton("⬅️ মেনু",         callback_data="main_menu")],
        ])
    )
    return ConversationHandler.END


async def _handle_cod(query, order_id, order):
    """Handle Cash on Delivery — no screenshot needed."""
    payment_model.save(order_id, order["user_id"], "cod", "cod_no_screenshot")

    for admin_id in ADMIN_IDS:
        try:
            await query._bot.send_message(
                chat_id=admin_id,
                text=(
                    f"💵 *COD অর্ডার!*\n"
                    f"🆔 #{order_id} | {order['full_name']} | {order['phone']}\n"
                    f"💰 {taka(order['total'])}"
                ),
                parse_mode="Markdown",
                reply_markup=order_action_kb(order_id, "pending"),
            )
        except Exception as e:
            logger.error(f"COD admin notify failed: {e}")

    await query.edit_message_text(
        f"✅ *Cash on Delivery অর্ডার কনফার্ম হয়েছে!*\n\n"
        f"🆔 অর্ডার: #{order_id}\n"
        f"💰 ডেলিভারিতে পরিশোধ করুন: *{taka(order['total'])}*\n\n"
        "ডেলিভারি ম্যান ফোন করবে। ফোন রেডি রাখুন! 📞",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📋 আমার অর্ডার", callback_data="my_orders")
        ]])
    )
