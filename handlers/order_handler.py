"""
handlers/order_handler.py
==========================
Complete checkout flow using ConversationHandler.
Supports both single-product "Buy Now" and cart checkout.
Flow: Area → Name → Phone → Address → [Notes] → Confirm
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database.queries import (
    get_product, get_cart_items, create_order, add_order_items,
    update_product_stock, use_coupon, clear_cart, update_user_stats, log_event,
)
from keyboards.builder import (
    delivery_area_keyboard, order_confirm_keyboard, order_placed_keyboard,
)
from utils.helpers import (
    validate_bd_phone, validate_name, validate_address,
    safe_edit, safe_answer, notify_admins,
)
from utils.formatters import format_price, format_admin_new_order
from config.settings import DELIVERY_CHARGE_INSIDE_DHAKA, DELIVERY_CHARGE_OUTSIDE_DHAKA

logger = logging.getLogger(__name__)

# ─── Conversation States ──────────────────────────────────────────────────────
(AREA, NAME, PHONE, ADDRESS, NOTES, CONFIRM) = range(10, 16)


async def start_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Entry point: Buy Now button — order_<product_id>.
    Stores single product in session, starts checkout.
    """
    query = update.callback_query
    await safe_answer(query)

    product_id = int(query.data.split("_")[1])
    product = get_product(product_id)

    if not product or product["stock"] <= 0:
        await query.answer("❌ পণ্যটি স্টকে নেই!", show_alert=True)
        return ConversationHandler.END

    # Store order session
    context.user_data["checkout"] = {
        "mode": "single",
        "items": [{
            "product_id":   product["product_id"],
            "product_name": product["name"],
            "unit_price":   float(product["discount_price"] or product["price"]),
            "quantity":     1,
            "max_stock":    product["stock"],
        }],
    }

    await safe_edit(
        query,
        f"🛒 *Order: {product['name']}*\n"
        f"💰 Price: *{format_price(product['discount_price'] or product['price'])}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*Step 1: Delivery Area*\n\n"
        f"আপনি কোথায় পণ্য পেতে চান?",
        reply_markup=delivery_area_keyboard()
    )
    return AREA


async def checkout_from_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start checkout from cart."""
    query = update.callback_query
    await safe_answer(query)
    user_id = update.effective_user.id

    items = get_cart_items(user_id)
    if not items:
        await query.answer("🛒 আপনার কার্ট খালি!", show_alert=True)
        return ConversationHandler.END

    # Validate stock
    for item in items:
        if item["quantity"] > item["stock"]:
            await query.answer(
                f"❌ '{item['name'][:20]}' স্টকে যথেষ্ট নেই!", show_alert=True
            )
            return ConversationHandler.END

    context.user_data["checkout"] = {
        "mode": "cart",
        "items": [{
            "product_id":   i["product_id"],
            "product_name": i["name"],
            "unit_price":   float(i["discount_price"] or i["price"]),
            "quantity":     i["quantity"],
            "max_stock":    i["stock"],
        } for i in items],
    }

    subtotal = sum(i["unit_price"] * i["quantity"] for i in context.user_data["checkout"]["items"])
    items_text = ", ".join(
        f"{i['product_name'][:15]} x{i['quantity']}"
        for i in context.user_data["checkout"]["items"]
    )

    await safe_edit(
        query,
        f"🛒 *Cart Checkout*\n\n"
        f"📦 Items: {items_text}\n"
        f"💰 Subtotal: *{format_price(subtotal)}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*Step 1: Delivery Area*\n\nআপনি কোথায় পণ্য পেতে চান?",
        reply_markup=delivery_area_keyboard()
    )
    return AREA


async def get_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive delivery area selection."""
    query = update.callback_query
    await safe_answer(query)

    area = "inside" if query.data == "area_inside" else "outside"
    charge = DELIVERY_CHARGE_INSIDE_DHAKA if area == "inside" else DELIVERY_CHARGE_OUTSIDE_DHAKA
    context.user_data["checkout"]["delivery_area"] = area
    context.user_data["checkout"]["delivery_charge"] = charge

    area_text = "🏙️ Inside Dhaka" if area == "inside" else "🗺️ Outside Dhaka"

    await safe_edit(
        query,
        f"✅ Delivery: *{area_text}* (৳{charge})\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*Step 2: আপনার নাম*\n\n"
        f"আপনার পূর্ণ নাম লিখুন:\n"
        f"_(উদাহরণ: Rahim Uddin)_",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_order")
        ]])
    )
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and validate customer name."""
    ok, result = validate_name(update.message.text)
    if not ok:
        await update.message.reply_text(result, parse_mode="Markdown")
        return NAME

    context.user_data["checkout"]["full_name"] = result

    await update.message.reply_text(
        f"✅ নাম সংরক্ষিত: *{result}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*Step 3: মোবাইল নম্বর*\n\n"
        f"আপনার মোবাইল নম্বর লিখুন:\n"
        f"_(উদাহরণ: 01712345678)_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_order")
        ]])
    )
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and validate phone number."""
    phone = update.message.text.strip().replace(" ", "").replace("-", "")
    if not validate_bd_phone(phone):
        await update.message.reply_text(
            "⚠️ ভুল নম্বর! বাংলাদেশি নম্বর দিন:\n_(Format: 01712345678)_",
            parse_mode="Markdown"
        )
        return PHONE

    context.user_data["checkout"]["phone"] = phone

    await update.message.reply_text(
        f"✅ নম্বর সংরক্ষিত: *{phone}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*Step 4: ডেলিভারি ঠিকানা*\n\n"
        f"আপনার সম্পূর্ণ ঠিকানা লিখুন:\n"
        f"_(বাড়ি নং, রোড, এলাকা, থানা, জেলা সহ)_\n"
        f"_উদাহরণ: বাড়ি ৫, রোড ৩, ধানমণ্ডি, ঢাকা_",
        parse_mode="Markdown",
    )
    return ADDRESS


async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive and validate address."""
    ok, result = validate_address(update.message.text)
    if not ok:
        await update.message.reply_text(result, parse_mode="Markdown")
        return ADDRESS

    context.user_data["checkout"]["address"] = result

    await update.message.reply_text(
        f"✅ ঠিকানা সংরক্ষিত!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*Step 5: বিশেষ নির্দেশনা (ঐচ্ছিক)*\n\n"
        f"কোনো বিশেষ নির্দেশনা থাকলে লিখুন\n"
        f"_(রং, সাইজ, বা অন্য তথ্য)_\n\n"
        f"কিছু না থাকলে *skip* লিখুন:",
        parse_mode="Markdown",
    )
    return NOTES


async def get_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive optional notes, then show order summary."""
    notes_text = update.message.text.strip()
    notes = None if notes_text.lower() in ("skip", "none", "no", "") else notes_text
    context.user_data["checkout"]["notes"] = notes

    return await _show_order_summary(update, context)


async def _show_order_summary(update, context):
    """Build and display the order confirmation summary."""
    co = context.user_data["checkout"]
    items = co["items"]
    subtotal = sum(i["unit_price"] * i["quantity"] for i in items)
    delivery = co.get("delivery_charge", 120)
    discount = co.get("discount", 0)
    total = subtotal + delivery - discount

    co["subtotal"] = round(subtotal, 2)
    co["total_price"] = round(total, 2)

    items_lines = "\n".join(
        f"  • {i['product_name'][:25]} × {i['quantity']} = {format_price(i['unit_price'] * i['quantity'])}"
        for i in items
    )
    area_text = "🏙️ Inside Dhaka" if co.get("delivery_area") == "inside" else "🗺️ Outside Dhaka"
    disc_line = f"\n🎫 *Discount:* -{format_price(discount)}" if discount else ""
    coupon_line = f"\n🎟️ *Coupon:* {co.get('coupon_code', '—')}" if co.get("coupon_code") else ""
    notes_line = f"\n📝 *Notes:* {co.get('notes')}" if co.get("notes") else ""
    method_map = {"bkash": "💜 bKash", "nagad": "🟠 Nagad", "cod": "💵 Cash on Delivery"}
    method = method_map.get(co.get("payment_method", ""), "—")

    summary = (
        f"📋 *Order Summary*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 *Items:*\n{items_lines}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Name:* {co['full_name']}\n"
        f"📞 *Phone:* {co['phone']}\n"
        f"📍 *Address:* {co['address']}"
        f"{notes_line}\n"
        f"📍 *Area:* {area_text}"
        f"{coupon_line}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🧾 *Subtotal:* {format_price(subtotal)}\n"
        f"🚚 *Delivery:* {format_price(delivery)}"
        f"{disc_line}\n"
        f"💵 *Total: {format_price(total)}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ অর্ডার নিশ্চিত করুন:"
    )

    await update.message.reply_text(
        summary,
        parse_mode="Markdown",
        reply_markup=order_confirm_keyboard()
    )
    return CONFIRM


async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Final step: save order, notify admin, clear cart."""
    query = update.callback_query
    await safe_answer(query)

    if query.data == "cancel_order":
        return await cancel_order(update, context)

    co = context.user_data.get("checkout", {})
    user_id = update.effective_user.id

    # Determine payment method (default: pending selection)
    payment_method = co.get("payment_method", "bkash")

    # Create order record
    order_id = create_order(
        user_id=user_id,
        full_name=co["full_name"],
        phone=co["phone"],
        address=co["address"],
        delivery_area=co.get("delivery_area", "outside"),
        subtotal=co["subtotal"],
        delivery_charge=co.get("delivery_charge", 120),
        total_price=co["total_price"],
        payment_method=payment_method,
        coupon_code=co.get("coupon_code"),
        discount=co.get("discount", 0),
        notes=co.get("notes"),
    )

    # Save order items and update stock
    items = co["items"]
    add_order_items(order_id, items)
    for item in items:
        update_product_stock(item["product_id"], item["quantity"])

    # Use coupon if applied
    if co.get("coupon_code"):
        use_coupon(co["coupon_code"])

    # Update user stats
    update_user_stats(user_id, co["total_price"])

    # Clear cart if checkout was from cart
    if co.get("mode") == "cart":
        clear_cart(user_id)

    # Log analytics
    log_event("order_placed", user_id=user_id, order_id=order_id, value=co["total_price"])

    # Store order_id for payment step
    context.user_data["last_order_id"] = order_id
    context.user_data.pop("checkout", None)

    items_summary = ", ".join(
        f"{i['product_name'][:15]} x{i['quantity']}" for i in items
    )

    await safe_edit(
        query,
        f"🎉 *অর্ডার সফলভাবে দেওয়া হয়েছে!*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *Order ID:* `#{order_id}`\n"
        f"📦 *Items:* {items_summary}\n"
        f"💰 *Total:* *{format_price(co['total_price'])}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 *পরবর্তী পদক্ষেপ:*\n"
        f"পেমেন্ট করুন এবং স্ক্রিনশট আপলোড করুন। ✅",
        reply_markup=order_placed_keyboard(order_id)
    )

    # Notify admins
    admin_text = format_admin_new_order(order_id, {
        "full_name": co["full_name"],
        "phone": co["phone"],
        "address": co["address"],
        "items_summary": items_summary,
        "total_price": co["total_price"],
        "payment_method": payment_method,
        "user_id": user_id,
    })
    await notify_admins(context, admin_text, parse_mode="Markdown")

    return ConversationHandler.END


async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel checkout conversation."""
    context.user_data.pop("checkout", None)

    if update.callback_query:
        await safe_answer(update.callback_query)
        await safe_edit(
            update.callback_query,
            "❌ *অর্ডার বাতিল করা হয়েছে।*\n\nআবার শুরু করতে মেনু থেকে পণ্য বেছে নিন।",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
            ]])
        )
    elif update.message:
        await update.message.reply_text(
            "❌ অর্ডার বাতিল। /start দিয়ে মেনুতে যান।"
        )
    return ConversationHandler.END


# ─── Coupon Application ───────────────────────────────────────────────────────

COUPON_STATE = 50


async def use_coupon_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt user to enter coupon code."""
    query = update.callback_query
    await safe_answer(query)
    await safe_edit(
        query,
        "🎫 *Coupon Code*\n\n"
        "আপনার কুপন কোড লিখুন:\n"
        "_(উদাহরণ: PICKDEAL10)_\n\n"
        "_কুপন কোড ব্যবহার করতে আগে কার্টে পণ্য যোগ করুন।_",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="main_menu")
        ]])
    )
    return COUPON_STATE


async def apply_coupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Apply coupon to the pending checkout."""
    from database.queries import validate_coupon
    from utils.helpers import calculate_discount

    code = update.message.text.strip().upper()
    user_id = update.effective_user.id

    # Get current cart subtotal for minimum order check
    items = get_cart_items(user_id)
    subtotal = sum((i["discount_price"] or i["price"]) * i["quantity"] for i in items)

    coupon = validate_coupon(code, subtotal)
    if not coupon:
        await update.message.reply_text(
            f"❌ কুপন কোড `{code}` অবৈধ বা মেয়াদ শেষ!\n\n"
            f"• কুপন কোডটি সঠিক কিনা দেখুন\n"
            f"• ন্যূনতম অর্ডার পরিমাণ পূরণ হয়েছে কিনা দেখুন",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
            ]])
        )
        return ConversationHandler.END

    discount, final = calculate_discount(subtotal, coupon)

    # Store in checkout session
    if "checkout" not in context.user_data:
        context.user_data["checkout"] = {}
    context.user_data["checkout"]["coupon_code"] = code
    context.user_data["checkout"]["discount"] = discount

    await update.message.reply_text(
        f"✅ *কুপন '{code}' সফলভাবে প্রয়োগ হয়েছে!*\n\n"
        f"💰 Subtotal: {format_price(subtotal)}\n"
        f"🎫 Discount: -{format_price(discount)}\n"
        f"💵 After Discount: *{format_price(final)}*\n\n"
        f"_(ডেলিভারি চার্জ আলাদা যুক্ত হবে)_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 Checkout",     callback_data="checkout")],
            [InlineKeyboardButton("🏠 Main Menu",    callback_data="main_menu")],
        ])
    )
    return ConversationHandler.END
