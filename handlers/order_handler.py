"""
handlers/order_handler.py
==========================
Handles the multi-step order form using ConversationHandler.
Flow: Product selected → Name → Phone → Address → Quantity → Confirm
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database.queries import get_product, create_order, validate_coupon, use_coupon
from utils.helpers import format_price, is_admin, ADMIN_IDS

logger = logging.getLogger(__name__)

# ─── Conversation States ──────────────────────────────────────────────────────
NAME     = 1
PHONE    = 2
ADDRESS  = 3
QUANTITY = 4
CONFIRM  = 5


async def start_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Entry point for the order flow.
    Triggered by 'order_<product_id>' callback button.
    """
    query = update.callback_query
    await query.answer()

    # Extract product ID
    product_id = int(query.data.split("_")[1])
    product = get_product(product_id)

    if not product:
        await query.answer("❌ Product not found!", show_alert=True)
        return ConversationHandler.END

    if product["stock"] <= 0:
        await query.answer("❌ Sorry, this product is out of stock!", show_alert=True)
        return ConversationHandler.END

    # Save product info in user session
    context.user_data["order"] = {
        "product_id":   product_id,
        "product_name": product["name"],
        "price":        product["price"],
        "max_stock":    product["stock"],
    }

    await query.edit_message_text(
        f"🛒 *Starting Order for:*\n*{product['name']}*\n"
        f"💰 Price: {format_price(product['price'])}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*Step 1 of 4: Your Name*\n\n"
        f"Please enter your *full name*:\n"
        f"_(Example: Rahim Uddin)_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_order")
        ]])
    )
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and validate customer name."""
    name = update.message.text.strip()

    if len(name) < 3:
        await update.message.reply_text(
            "⚠️ Name is too short. Please enter your *full name* (at least 3 characters):",
            parse_mode="Markdown"
        )
        return NAME

    if len(name) > 60:
        await update.message.reply_text("⚠️ Name is too long. Please keep it under 60 characters:")
        return NAME

    context.user_data["order"]["name"] = name

    await update.message.reply_text(
        f"✅ Name saved: *{name}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*Step 2 of 4: Phone Number*\n\n"
        f"Please enter your *mobile number*:\n"
        f"_(Example: 01712345678)_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="main_menu")
        ]])
    )
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and validate phone number."""
    phone = update.message.text.strip().replace(" ", "").replace("-", "")

    # Basic Bangladesh phone validation (01XXXXXXXXX)
    if not (phone.startswith("01") and len(phone) == 11 and phone.isdigit()):
        await update.message.reply_text(
            "⚠️ Invalid phone number!\n"
            "Please enter a valid Bangladeshi number:\n"
            "_(Format: 01712345678)_",
            parse_mode="Markdown"
        )
        return PHONE

    context.user_data["order"]["phone"] = phone

    await update.message.reply_text(
        f"✅ Phone saved: *{phone}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*Step 3 of 4: Delivery Address*\n\n"
        f"Please enter your *full delivery address*:\n"
        f"_(Include: House/Road, Area, Thana, District)_\n\n"
        f"_Example: House 5, Road 3, Dhanmondi, Dhaka_",
        parse_mode="Markdown",
    )
    return ADDRESS


async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and validate delivery address."""
    address = update.message.text.strip()

    if len(address) < 10:
        await update.message.reply_text(
            "⚠️ Address is too short. Please provide your *full delivery address*:",
            parse_mode="Markdown"
        )
        return ADDRESS

    context.user_data["order"]["address"] = address

    await update.message.reply_text(
        f"✅ Address saved!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*Step 4 of 4: Quantity*\n\n"
        f"How many units do you want?\n"
        f"_(Max: {context.user_data['order']['max_stock']} in stock)_",
        parse_mode="Markdown",
    )
    return QUANTITY


async def get_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and validate quantity, then show order confirmation."""
    text = update.message.text.strip()

    if not text.isdigit():
        await update.message.reply_text("⚠️ Please enter a *number* (e.g. 1, 2, 3):", parse_mode="Markdown")
        return QUANTITY

    qty = int(text)
    max_stock = context.user_data["order"]["max_stock"]

    if qty < 1:
        await update.message.reply_text("⚠️ Quantity must be at least 1.")
        return QUANTITY

    if qty > max_stock:
        await update.message.reply_text(
            f"⚠️ Only *{max_stock}* items available. Please enter a valid quantity:",
            parse_mode="Markdown"
        )
        return QUANTITY

    if qty > 10:
        await update.message.reply_text(
            "⚠️ Max 10 units per order. Please enter a valid quantity:"
        )
        return QUANTITY

    order = context.user_data["order"]
    order["quantity"] = qty

    # Calculate total (no coupon at this step)
    total = order["price"] * qty
    order["total_price"] = total
    order["discount"] = 0
    order["coupon_code"] = None

    # Build order summary
    summary = (
        f"📋 *Order Summary*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 *Product:* {order['product_name']}\n"
        f"🔢 *Quantity:* {qty}\n"
        f"💰 *Unit Price:* {format_price(order['price'])}\n"
        f"💵 *Total:* {format_price(total)}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Name:* {order['name']}\n"
        f"📞 *Phone:* {order['phone']}\n"
        f"📍 *Address:* {order['address']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Please confirm your order:"
    )

    await update.message.reply_text(
        summary,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("✅ Confirm Order", callback_data="confirm_order"),
                InlineKeyboardButton("❌ Cancel",        callback_data="cancel_order"),
            ]
        ])
    )
    return CONFIRM


async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Final step: Save order to database and notify admin.
    """
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_order":
        return await cancel_order(update, context)

    order = context.user_data.get("order", {})
    user_id = update.effective_user.id

    # Save order to database
    order_id = create_order(
        user_id     = user_id,
        product_id  = order["product_id"],
        quantity    = order["quantity"],
        total_price = order["total_price"],
        full_name   = order["name"],
        phone       = order["phone"],
        address     = order["address"],
        coupon_code = order.get("coupon_code"),
        discount    = order.get("discount", 0),
    )

    # Store order_id in session for payment step
    context.user_data["last_order_id"] = order_id

    success_text = (
        f"🎉 *Order Placed Successfully!*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *Your Order ID:* `#{order_id}`\n"
        f"📦 *Product:* {order['product_name']}\n"
        f"💰 *Total:* {format_price(order['total_price'])}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 *Next Step:*\n"
        f"Please complete payment to confirm your order."
    )

    await query.edit_message_text(
        success_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💳 Pay Now", callback_data=f"pay_order_{order_id}")],
            [InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")],
        ])
    )

    # ─── Notify Admin ─────────────────────────────────────────────────────────
    admin_text = (
        f"🔔 *New Order Received!*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *Order ID:* #{order_id}\n"
        f"👤 *Customer:* {order['name']}\n"
        f"📞 *Phone:* {order['phone']}\n"
        f"📍 *Address:* {order['address']}\n"
        f"📦 *Product:* {order['product_name']}\n"
        f"🔢 *Qty:* {order['quantity']}\n"
        f"💰 *Total:* {format_price(order['total_price'])}\n"
        f"👤 *Telegram ID:* {user_id}"
    )

    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                parse_mode="Markdown",
            )
        except Exception as e:
            logger.error(f"Failed to notify admin {admin_id}: {e}")

    # Clear order data from session
    context.user_data.pop("order", None)

    return ConversationHandler.END


async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the current order conversation."""
    context.user_data.pop("order", None)

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "❌ *Order cancelled.*\n\nYou can start a new order anytime!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")
            ]])
        )
    else:
        await update.message.reply_text(
            "❌ Order cancelled. Use /start to return to menu.",
        )

    return ConversationHandler.END
