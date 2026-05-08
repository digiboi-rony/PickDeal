"""
handlers/payment_handler.py
============================
Handles payment instructions and screenshot submission.
Customer uploads a bKash/Nagad screenshot → bot forwards to admin.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database.queries import get_order, save_payment, update_order_status
from utils.helpers import format_price, BKASH_NUMBER, NAGAD_NUMBER, ADMIN_IDS

logger = logging.getLogger(__name__)

# Conversation state
WAITING_SCREENSHOT = 20


async def show_payment_instructions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show payment instructions for a specific order.
    Triggered by 'pay_order_<order_id>' callback.
    """
    query = update.callback_query
    await query.answer()

    # Extract order ID from callback
    order_id = int(query.data.split("_")[2])
    order = get_order(order_id)

    if not order:
        await query.answer("❌ Order not found!", show_alert=True)
        return ConversationHandler.END

    # Verify this order belongs to the user
    if order["user_id"] != update.effective_user.id:
        await query.answer("❌ Unauthorized!", show_alert=True)
        return ConversationHandler.END

    # Store order_id for screenshot step
    context.user_data["paying_order_id"] = order_id

    total = format_price(order["total_price"])

    payment_text = (
        f"💳 *Payment Instructions*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *Order ID:* #{order_id}\n"
        f"💰 *Amount to Pay:* {total}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📱 *Pay via bKash:*\n"
        f"Number: `{BKASH_NUMBER}`\n"
        f"Type: Send Money\n\n"
        f"📱 *Pay via Nagad:*\n"
        f"Number: `{NAGAD_NUMBER}`\n"
        f"Type: Send Money\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ *Important:*\n"
        f"• Send exact amount: {total}\n"
        f"• Use 'Send Money' (not Request)\n"
        f"• After payment, upload the screenshot below\n\n"
        f"📸 *Please send your payment screenshot now:*"
    )

    await query.edit_message_text(
        payment_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="main_menu")
        ]])
    )

    return WAITING_SCREENSHOT


async def receive_payment_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Receive payment screenshot from customer.
    Saves it to database and forwards it to admin.
    """
    user = update.effective_user
    order_id = context.user_data.get("paying_order_id")

    if not order_id:
        await update.message.reply_text(
            "⚠️ Session expired. Please start again from your order."
        )
        return ConversationHandler.END

    order = get_order(order_id)
    if not order:
        await update.message.reply_text("❌ Order not found.")
        return ConversationHandler.END

    # Get the highest resolution photo (last in the list = best quality)
    photo = update.message.photo[-1]
    file_id = photo.file_id

    # Save payment record to database
    save_payment(
        order_id      = order_id,
        user_id       = user.id,
        method        = "bKash/Nagad",  # Customer can specify in caption
        screenshot_id = file_id,
        trx_ref       = update.message.caption or None,
    )

    # Update order status to indicate payment submitted
    update_order_status(order_id, "pending")

    # ─── Notify Admin with Screenshot ─────────────────────────────────────────
    admin_caption = (
        f"💳 *New Payment Screenshot*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *Order ID:* #{order_id}\n"
        f"👤 *Customer:* {order['full_name']}\n"
        f"📞 *Phone:* {order['phone']}\n"
        f"📦 *Product:* {order['product_name']}\n"
        f"💰 *Amount:* {format_price(order['total_price'])}\n"
        f"👤 *Telegram ID:* {user.id}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Tap below to update order status:"
    )

    # Admin action buttons for this order
    admin_buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirm Payment",  callback_data=f"admin_update_{order_id}_confirmed")],
        [InlineKeyboardButton("❌ Reject Payment",   callback_data=f"admin_update_{order_id}_cancelled")],
    ])

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_photo(
                chat_id       = admin_id,
                photo         = file_id,
                caption       = admin_caption,
                parse_mode    = "Markdown",
                reply_markup  = admin_buttons,
            )
        except Exception as e:
            logger.error(f"Failed to forward screenshot to admin {admin_id}: {e}")

    # ─── Confirm to Customer ──────────────────────────────────────────────────
    await update.message.reply_text(
        f"✅ *Payment screenshot received!*\n\n"
        f"🆔 *Order ID:* #{order_id}\n\n"
        f"Our team will verify your payment and confirm your order within 1-3 hours.\n\n"
        f"You'll receive a notification once confirmed! 🎉",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 My Orders",     callback_data="my_orders")],
            [InlineKeyboardButton("⬅️ Back to Menu",  callback_data="main_menu")],
        ])
    )

    # Clear session data
    context.user_data.pop("paying_order_id", None)

    return ConversationHandler.END
