"""
handlers/payment_handler.py
============================
Payment method selection, instructions, and screenshot submission.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database.queries import get_order, save_payment, update_order_status
from keyboards.builder import payment_cancel_keyboard
from utils.helpers import safe_edit, safe_answer, notify_admins
from utils.formatters import format_price, format_admin_payment_screenshot
from config.settings import BKASH_NUMBER, NAGAD_NUMBER, ADMIN_IDS

logger = logging.getLogger(__name__)

WAITING_SCREENSHOT = 20


async def select_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show payment method selection.
    Triggered by: payorder_<order_id>
    """
    query = update.callback_query
    await safe_answer(query)

    order_id = int(query.data.split("_")[1])
    order = get_order(order_id)

    if not order or order["user_id"] != update.effective_user.id:
        await query.answer("❌ অর্ডার পাওয়া যায়নি!", show_alert=True)
        return ConversationHandler.END

    context.user_data["paying_order_id"] = order_id
    total = format_price(order["total_price"])

    await safe_edit(
        query,
        f"💳 *Payment Method*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 Order ID: *#{order_id}*\n"
        f"💰 Amount: *{total}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"পেমেন্ট পদ্ধতি বেছে নিন:",
        reply_markup=_payment_method_kb(order_id)
    )
    return ConversationHandler.END


def _payment_method_kb(order_id: int) -> InlineKeyboardMarkup:
    from config.settings import COD_ENABLED
    buttons = [
        [InlineKeyboardButton("💜 bKash",             callback_data=f"pay_{order_id}_bkash")],
        [InlineKeyboardButton("🟠 Nagad",             callback_data=f"pay_{order_id}_nagad")],
    ]
    if COD_ENABLED:
        buttons.append([InlineKeyboardButton("💵 Cash on Delivery", callback_data=f"pay_{order_id}_cod")])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="my_orders")])
    return InlineKeyboardMarkup(buttons)


async def show_payment_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show payment instructions for a chosen method.
    Callback: pay_<order_id>_<method>
    """
    query = update.callback_query
    await safe_answer(query)

    parts = query.data.split("_")
    order_id = int(parts[1])
    method = parts[2]  # bkash / nagad / cod

    order = get_order(order_id)
    if not order or order["user_id"] != update.effective_user.id:
        await query.answer("❌ Unauthorized!", show_alert=True)
        return ConversationHandler.END

    context.user_data["paying_order_id"] = order_id
    context.user_data["paying_method"] = method
    total = format_price(order["total_price"])

    # COD — no screenshot needed
    if method == "cod":
        update_order_status(order_id, "pending")
        await safe_edit(
            query,
            f"✅ *Cash on Delivery নিশ্চিত!*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 Order ID: *#{order_id}*\n"
            f"💵 Amount: *{total}* (পণ্য পাওয়ার সময় দিন)\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"আমাদের ডেলিভারি টিম শীঘ্রই যোগাযোগ করবে! 🚚",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 My Orders", callback_data="my_orders")],
                [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
            ])
        )
        await notify_admins(
            update.get_bot() if hasattr(update, 'get_bot') else query,
            f"💵 *COD Order*\n"
            f"🆔 Order #{order_id}\n"
            f"👤 {order['full_name']}\n"
            f"📞 {order['phone']}\n"
            f"💰 {total}",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    # bKash or Nagad
    number = BKASH_NUMBER if method == "bkash" else NAGAD_NUMBER
    method_name = "bKash" if method == "bkash" else "Nagad"
    method_emoji = "💜" if method == "bkash" else "🟠"

    instructions = (
        f"{method_emoji} *{method_name} Payment*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 Order ID: *#{order_id}*\n"
        f"💰 Amount: *{total}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📱 *{method_name} নম্বর:*\n"
        f"`{number}`\n\n"
        f"🔄 *ধরন:* Send Money\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ *গুরুত্বপূর্ণ:*\n"
        f"• ঠিক *{total}* পাঠান\n"
        f"• 'Send Money' ব্যবহার করুন\n"
        f"• পেমেন্টের পর স্ক্রিনশট পাঠান\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📸 *এখন পেমেন্টের স্ক্রিনশট পাঠান:*"
    )

    await safe_edit(
        query,
        instructions,
        reply_markup=payment_cancel_keyboard()
    )
    return WAITING_SCREENSHOT


async def receive_payment_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive payment screenshot from customer."""
    user = update.effective_user
    order_id = context.user_data.get("paying_order_id")
    method = context.user_data.get("paying_method", "bkash")

    if not order_id:
        await update.message.reply_text("⚠️ Session expired. My Orders থেকে আবার চেষ্টা করুন।")
        return ConversationHandler.END

    order = get_order(order_id)
    if not order:
        await update.message.reply_text("❌ Order পাওয়া যায়নি।")
        return ConversationHandler.END

    photo = update.message.photo[-1]
    file_id = photo.file_id

    save_payment(
        order_id=order_id,
        user_id=user.id,
        method=method,
        screenshot_id=file_id,
        amount=order["total_price"],
        trx_ref=update.message.caption or None,
    )

    # ─── Notify Admins with screenshot ───────────────────────────────────────
    admin_caption = format_admin_payment_screenshot(order_id, order, user.id)
    admin_buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm Payment", callback_data=f"admupd_{order_id}_confirmed")],
        [InlineKeyboardButton("❌ Reject Payment",  callback_data=f"admupd_{order_id}_cancelled")],
    ])

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_photo(
                chat_id=admin_id,
                photo=file_id,
                caption=admin_caption,
                parse_mode="Markdown",
                reply_markup=admin_buttons,
            )
        except Exception as e:
            logger.error(f"Failed to forward screenshot to admin {admin_id}: {e}")

    # ─── Confirm to customer ──────────────────────────────────────────────────
    await update.message.reply_text(
        f"✅ *পেমেন্ট স্ক্রিনশট পাওয়া গেছে!*\n\n"
        f"🆔 Order ID: *#{order_id}*\n\n"
        f"আমাদের টিম ১–৩ ঘণ্টার মধ্যে ভেরিফাই করবে।\n"
        f"নিশ্চিত হলে আপনাকে জানানো হবে! 🎉",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 My Orders",  callback_data="my_orders")],
            [InlineKeyboardButton("🏠 Main Menu",  callback_data="main_menu")],
        ])
    )

    context.user_data.pop("paying_order_id", None)
    context.user_data.pop("paying_method", None)
    return ConversationHandler.END
