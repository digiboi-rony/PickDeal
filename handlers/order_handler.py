"""
handlers/order_handler.py — PickDeal BD v3
Full checkout: dynamic delivery from DB, coupon, confirm.
FIX: Delivery method selection now dynamic from delivery_methods table.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database.queries import (
    get_product, get_cart_items, get_delivery_methods, get_delivery_method,
    validate_coupon, use_coupon, calculate_coupon_discount,
    create_order, add_order_items, update_product_stock,
    clear_cart, update_user_stats, log_event, get_payment_methods,
)
from keyboards.builder import (
    delivery_methods_keyboard, order_confirm_keyboard, order_placed_keyboard,
)
from utils.helpers import (
    validate_bd_phone, validate_name, validate_address,
    safe_edit, safe_answer, notify_admins, calculate_discount,
)
from utils.formatters import format_price, format_admin_new_order

logger = logging.getLogger(__name__)

# ── States ────────────────────────────────────────────────────────
(DELIVERY, NAME, PHONE, ADDRESS, NOTES, CONFIRM) = range(10, 16)
COUPON_INPUT = 50


# ════════════════════════════════════════════════
# CHECKOUT ENTRY
# ════════════════════════════════════════════════

async def buy_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buy Now — single product."""
    query      = update.callback_query
    await safe_answer(query)
    product_id = int(query.data.split("_")[1])
    product    = get_product(product_id)

    if not product or product["stock"] <= 0:
        await query.answer("❌ পণ্যটি স্টকে নেই!", show_alert=True)
        return ConversationHandler.END

    context.user_data["checkout"] = {
        "mode": "single",
        "items": [{
            "product_id":   product["product_id"],
            "product_name": product["name"],
            "unit_price":   float(product["discount_price"] or product["price"]),
            "quantity":     1,
        }],
    }
    return await _start_delivery_step(update, context,
        f"🛒 *{product['name']}*\n💰 {format_price(product['discount_price'] or product['price'])}")


async def checkout_from_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Checkout from cart."""
    query   = update.callback_query
    await safe_answer(query)
    user_id = update.effective_user.id
    items   = get_cart_items(user_id)

    if not items:
        await query.answer("🛒 কার্ট খালি!", show_alert=True)
        return ConversationHandler.END

    for item in items:
        if item["quantity"] > item["stock"]:
            await query.answer(f"❌ '{item['name'][:20]}' স্টক যথেষ্ট নেই!", show_alert=True)
            return ConversationHandler.END

    context.user_data["checkout"] = {
        "mode": "cart",
        "items": [{
            "product_id":   i["product_id"],
            "product_name": i["name"],
            "unit_price":   float(i["discount_price"] or i["price"]),
            "quantity":     i["quantity"],
        } for i in items],
    }
    subtotal   = sum(i["unit_price"] * i["quantity"] for i in context.user_data["checkout"]["items"])
    items_text = ", ".join(f"{i['product_name'][:12]} ×{i['quantity']}"
                           for i in context.user_data["checkout"]["items"])
    return await _start_delivery_step(update, context,
        f"🛒 *কার্ট চেকআউট*\n📦 {items_text}\n💰 সাবটোটাল: {format_price(subtotal)}")


async def _start_delivery_step(update, context, header: str):
    """Show dynamic delivery method selection."""
    methods = get_delivery_methods(active_only=True)
    if not methods:
        query = update.callback_query
        await safe_edit(query,
            "⚠️ কোনো ডেলিভারি পদ্ধতি সক্রিয় নেই। Admin কে জানান।",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 মেইন মেনু", callback_data="main_menu")
            ]]))
        return ConversationHandler.END

    query = update.callback_query
    await safe_edit(query,
        f"{header}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*ধাপ ১: ডেলিভারি পদ্ধতি বেছে নিন:*",
        reply_markup=delivery_methods_keyboard(methods))
    return DELIVERY


# ════════════════════════════════════════════════
# CONVERSATION STEPS
# ════════════════════════════════════════════════

async def get_delivery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback: dlv_<method_id>"""
    query     = update.callback_query
    await safe_answer(query)
    method_id = int(query.data.split("_")[1])
    method    = get_delivery_method(method_id)

    if not method:
        await query.answer("❌ ডেলিভারি পদ্ধতি পাওয়া যায়নি!", show_alert=True)
        return DELIVERY

    context.user_data["checkout"]["delivery_method"] = method["name"]
    context.user_data["checkout"]["delivery_charge"]  = float(method["charge"])
    context.user_data["checkout"]["cod_allowed"]      = bool(method["cod_allowed"])

    await safe_edit(query,
        f"✅ ডেলিভারি: *{method['name']}* (৳{int(method['charge'])})\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"*ধাপ ২: আপনার সম্পূর্ণ নাম লিখুন:*",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ বাতিল", callback_data="cancel_checkout")
        ]]))
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ok, result = validate_name(update.message.text)
    if not ok:
        await update.message.reply_text(result, parse_mode="Markdown")
        return NAME
    context.user_data["checkout"]["full_name"] = result
    await update.message.reply_text(
        f"✅ নাম: *{result}*\n\n*ধাপ ৩: মোবাইল নম্বর লিখুন:*\n_(যেমন: 01712345678)_",
        parse_mode="Markdown")
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip().replace(" ", "").replace("-", "")
    if not validate_bd_phone(phone):
        await update.message.reply_text(
            "⚠️ সঠিক বাংলাদেশি নম্বর দিন:\n_(Format: 01XXXXXXXXX)_",
            parse_mode="Markdown")
        return PHONE
    context.user_data["checkout"]["phone"] = phone
    await update.message.reply_text(
        f"✅ নম্বর: *{phone}*\n\n*ধাপ ৪: ডেলিভারি ঠিকানা লিখুন:*\n"
        f"_(বাড়ি নং, রোড, এলাকা, থানা, জেলা সহ)_",
        parse_mode="Markdown")
    return ADDRESS


async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ok, result = validate_address(update.message.text)
    if not ok:
        await update.message.reply_text(result, parse_mode="Markdown")
        return ADDRESS
    context.user_data["checkout"]["address"] = result
    await update.message.reply_text(
        f"✅ ঠিকানা সংরক্ষিত!\n\n"
        f"*ধাপ ৫: বিশেষ নির্দেশনা (ঐচ্ছিক)*\n"
        f"_(রং, সাইজ বা অন্য তথ্য — না থাকলে *skip* লিখুন)_",
        parse_mode="Markdown")
    return NOTES


async def get_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    context.user_data["checkout"]["notes"] = (
        None if txt.lower() in ("skip", "none", "না", "") else txt
    )
    return await _show_summary(update, context)


async def _show_summary(update, context):
    co       = context.user_data["checkout"]
    items    = co["items"]
    subtotal = sum(i["unit_price"] * i["quantity"] for i in items)
    delivery = co.get("delivery_charge", 120)
    discount = co.get("discount", 0)
    total    = subtotal + delivery - discount

    co["subtotal"]    = round(subtotal, 2)
    co["total_price"] = round(total, 2)

    items_lines = "\n".join(
        f"  • {i['product_name'][:24]} × {i['quantity']} = {format_price(i['unit_price'] * i['quantity'])}"
        for i in items
    )
    disc_line   = f"\n🎫 *ডিসকাউন্ট:* -{format_price(discount)}" if discount else ""
    coupon_line = f"\n🎟️ *কুপন:* {co.get('coupon_code', '—')}" if co.get("coupon_code") else ""
    notes_line  = f"\n📝 *নোট:* {co.get('notes')}" if co.get("notes") else ""

    await update.message.reply_text(
        f"📋 *অর্ডার সারসংক্ষেপ*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 *পণ্য:*\n{items_lines}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *নাম:* {co['full_name']}\n"
        f"📞 *ফোন:* {co['phone']}\n"
        f"📍 *ঠিকানা:* {co['address']}"
        f"{notes_line}\n"
        f"🚚 *ডেলিভারি:* {co.get('delivery_method', '—')}"
        f"{coupon_line}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🧾 *সাবটোটাল:* {format_price(subtotal)}\n"
        f"🚚 *ডেলিভারি চার্জ:* {format_price(delivery)}"
        f"{disc_line}\n"
        f"💵 *মোট: {format_price(total)}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ অর্ডার নিশ্চিত করুন:",
        parse_mode="Markdown",
        reply_markup=order_confirm_keyboard())
    return CONFIRM


async def confirm_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    if query.data == "cancel_checkout":
        return await cancel_checkout(update, context)

    co      = context.user_data.get("checkout", {})
    user_id = update.effective_user.id

    order_id = create_order(
        user_id         = user_id,
        full_name       = co["full_name"],
        phone           = co["phone"],
        address         = co["address"],
        delivery_method = co.get("delivery_method", "—"),
        delivery_charge = co.get("delivery_charge", 0),
        subtotal        = co["subtotal"],
        total_price     = co["total_price"],
        payment_method  = "pending",
        advance_amount  = co.get("advance_amount", 0),
        coupon_code     = co.get("coupon_code"),
        discount        = co.get("discount", 0),
        notes           = co.get("notes"),
    )

    items = co["items"]
    add_order_items(order_id, items)
    for item in items:
        update_product_stock(item["product_id"], item["quantity"])

    if co.get("coupon_code"):
        use_coupon(co["coupon_code"])

    update_user_stats(user_id, co["total_price"])
    if co.get("mode") == "cart":
        clear_cart(user_id)

    log_event("order_placed", user_id=user_id, order_id=order_id, value=co["total_price"])

    items_summary = ", ".join(
        f"{i['product_name'][:12]} ×{i['quantity']}" for i in items
    )
    context.user_data["last_order_id"] = order_id
    context.user_data.pop("checkout", None)

    # ── Step: Now choose payment method ──────────────────────────
    methods = get_payment_methods(active_only=True)
    if not methods:
        await safe_edit(query,
            f"✅ *অর্ডার তৈরি হয়েছে!*\n"
            f"🆔 Order ID: `#{order_id}`\n\n"
            f"⚠️ পেমেন্ট পদ্ধতি পাওয়া যায়নি। Admin কে জানান।",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📋 আমার অর্ডার", callback_data="my_orders")
            ]]))
        return ConversationHandler.END

    from keyboards.builder import payment_methods_keyboard
    await safe_edit(query,
        f"✅ *অর্ডার কনফার্ম হয়েছে!*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *Order ID:* `#{order_id}`\n"
        f"📦 *পণ্য:* {items_summary}\n"
        f"💰 *মোট:* {format_price(co['total_price'])}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💳 *এখন পেমেন্ট পদ্ধতি বেছে নিন:*",
        reply_markup=payment_methods_keyboard(methods, order_id))

    admin_text = format_admin_new_order(order_id, {
        "full_name": co["full_name"], "phone": co["phone"],
        "address": co["address"], "delivery_method": co.get("delivery_method"),
        "items_summary": items_summary, "total_price": co["total_price"],
        "payment_method": "pending", "user_id": user_id,
    })
    await notify_admins(context, admin_text, parse_mode="Markdown")
    return ConversationHandler.END


async def cancel_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("checkout", None)
    if update.callback_query:
        await safe_answer(update.callback_query)
        await safe_edit(update.callback_query,
            "❌ *চেকআউট বাতিল হয়েছে।*",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 মেইন মেনু", callback_data="main_menu")
            ]]))
    elif update.message:
        await update.message.reply_text("❌ বাতিল। /start দিয়ে মেনুতে যান।")
    return ConversationHandler.END


# ════════════════════════════════════════════════
# COUPON
# ════════════════════════════════════════════════

async def coupon_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    await safe_edit(query,
        "🎫 *কুপন কোড*\n\nআপনার কুপন কোড লিখুন:\n_(যেমন: PICKDEAL10)_",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ বাতিল", callback_data="main_menu")
        ]]))
    return COUPON_INPUT


async def apply_coupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database.queries import get_cart_items
    code    = update.message.text.strip().upper()
    user_id = update.effective_user.id
    items   = get_cart_items(user_id)
    subtotal = sum(
        float(i["discount_price"] or i["price"]) * i["quantity"] for i in items
    )
    coupon = validate_coupon(code, subtotal)
    if not coupon:
        await update.message.reply_text(
            f"❌ কুপন `{code}` অবৈধ বা মেয়াদ শেষ!\n"
            f"• কোডটি সঠিক কিনা দেখুন\n"
            f"• ন্যূনতম অর্ডার শর্ত পূরণ হয়েছে কিনা দেখুন",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 মেইন মেনু", callback_data="main_menu")
            ]]))
        return ConversationHandler.END

    discount = calculate_coupon_discount(coupon, subtotal)
    if "checkout" not in context.user_data:
        context.user_data["checkout"] = {}
    context.user_data["checkout"]["coupon_code"] = code
    context.user_data["checkout"]["discount"]    = discount

    await update.message.reply_text(
        f"✅ *কুপন '{code}' সফলভাবে প্রয়োগ হয়েছে!*\n\n"
        f"💰 সাবটোটাল: {format_price(subtotal)}\n"
        f"🎫 ডিসকাউন্ট: -{format_price(discount)}\n"
        f"💵 ডিসকাউন্টের পরে: *{format_price(subtotal - discount)}*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 চেকআউট", callback_data="checkout")],
            [InlineKeyboardButton("🏠 মেইন মেনু", callback_data="main_menu")],
        ]))
    return ConversationHandler.END
