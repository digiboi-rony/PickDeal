"""
handlers/order_handler.py — v3.2
NEW FLOW: Delivery → Name → Phone → Address → Notes → Payment Method → Confirm
Professional anti-spam: user must complete all steps before order placed.
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database.queries import (
    get_product, get_cart_items, get_delivery_methods, get_delivery_method,
    get_payment_methods, validate_coupon, use_coupon, calculate_coupon_discount,
    create_order, add_order_items, update_product_stock,
    clear_cart, update_user_stats, log_event,
)
from keyboards.builder import delivery_methods_keyboard, payment_methods_keyboard, order_confirm_keyboard, order_placed_keyboard
from utils.helpers import validate_bd_phone, validate_name, validate_address, safe_edit, safe_answer, notify_admins, calculate_discount
from utils.formatters import format_price, format_admin_new_order

logger = logging.getLogger(__name__)

# States
(DELIVERY, NAME, PHONE, ADDRESS, NOTES, PAYMENT, CONFIRM) = range(10, 17)
COUPON_INPUT = 50


def _g(row, key, default=None):
    try:
        v = row[key]
        return v if v is not None else default
    except (KeyError, IndexError, TypeError):
        return default


async def buy_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query      = update.callback_query
    await safe_answer(query)
    product_id = int(query.data.split("_")[1])
    product    = get_product(product_id)
    if not product or int(_g(product, "stock", 0) or 0) <= 0:
        await query.answer("❌ পণ্যটি স্টকে নেই!", show_alert=True)
        return ConversationHandler.END
    context.user_data["checkout"] = {
        "mode": "single",
        "items": [{
            "product_id":   _g(product, "product_id"),
            "product_name": _g(product, "name"),
            "unit_price":   float(_g(product, "discount_price") or _g(product, "price", 0)),
            "quantity":     1,
        }],
    }
    price_txt = format_price(_g(product, "discount_price") or _g(product, "price", 0))
    return await _start_delivery_step(update, context,
        f"🛒 *{_g(product,'name')}*\n💰 {price_txt}")


async def checkout_from_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await safe_answer(query)
    user_id = update.effective_user.id
    items   = get_cart_items(user_id)
    if not items:
        await query.answer("🛒 কার্ট খালি!", show_alert=True)
        return ConversationHandler.END
    for item in items:
        if int(_g(item, "quantity", 1)) > int(_g(item, "stock", 0) or 0):
            await query.answer(f"❌ '{_g(item,'name','?')[:18]}' স্টক যথেষ্ট নেই!", show_alert=True)
            return ConversationHandler.END
    context.user_data["checkout"] = {
        "mode": "cart",
        "items": [{
            "product_id":   _g(i, "product_id"),
            "product_name": _g(i, "name"),
            "unit_price":   float(_g(i, "discount_price") or _g(i, "price", 0)),
            "quantity":     int(_g(i, "quantity", 1)),
        } for i in items],
    }
    subtotal   = sum(i["unit_price"] * i["quantity"] for i in context.user_data["checkout"]["items"])
    items_text = ", ".join(f"{i['product_name'][:12]} ×{i['quantity']}"
                           for i in context.user_data["checkout"]["items"])
    return await _start_delivery_step(update, context,
        f"🛒 *কার্ট চেকআউট*\n📦 {items_text}\n💰 সাবটোটাল: {format_price(subtotal)}")


async def _start_delivery_step(update, context, header: str):
    methods = get_delivery_methods(active_only=True)
    if not methods:
        query = update.callback_query
        await safe_edit(query, "⚠️ কোনো ডেলিভারি পদ্ধতি নেই। Admin কে জানান।",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 মেনু", callback_data="main_menu")]]))
        return ConversationHandler.END
    query = update.callback_query
    await safe_edit(query,
        f"{header}\n\n━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 *ধাপ ১/৬ — ডেলিভারি পদ্ধতি*\n\nকোথায় ডেলিভারি চান?",
        reply_markup=delivery_methods_keyboard(methods))
    return DELIVERY


async def get_delivery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await safe_answer(query)
    method_id = int(query.data.split("_")[1])
    method    = get_delivery_method(method_id)
    if not method:
        await query.answer("❌ পাওয়া যায়নি!", show_alert=True)
        return DELIVERY
    context.user_data["checkout"]["delivery_method"]  = _g(method, "name")
    context.user_data["checkout"]["delivery_charge"]  = float(_g(method, "charge", 0) or 0)
    context.user_data["checkout"]["cod_allowed"]      = bool(_g(method, "cod_allowed"))
    await safe_edit(query,
        f"✅ ডেলিভারি: *{_g(method,'name')}* (৳{int(float(_g(method,'charge',0) or 0))})\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *ধাপ ২/৬ — আপনার সম্পূর্ণ নাম লিখুন:*",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data="cancel_checkout")]]))
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ok, result = validate_name(update.message.text)
    if not ok:
        await update.message.reply_text(result, parse_mode="Markdown")
        return NAME
    context.user_data["checkout"]["full_name"] = result
    await update.message.reply_text(
        f"✅ নাম: *{result}*\n\n━━━━━━━━━━━━━━━━━━━━\n"
        f"📞 *ধাপ ৩/৬ — মোবাইল নম্বর লিখুন:*\n_(যেমন: 01712345678)_",
        parse_mode="Markdown")
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    phone = update.message.text.strip().replace(" ", "").replace("-", "")
    if not validate_bd_phone(phone):
        await update.message.reply_text("⚠️ সঠিক বাংলাদেশি নম্বর দিন:\n_(Format: 01XXXXXXXXX)_", parse_mode="Markdown")
        return PHONE
    context.user_data["checkout"]["phone"] = phone
    await update.message.reply_text(
        f"✅ নম্বর: *{phone}*\n\n━━━━━━━━━━━━━━━━━━━━\n"
        f"📍 *ধাপ ৪/৬ — ডেলিভারি ঠিকানা লিখুন:*\n_(বাড়ি নং, রোড, এলাকা, থানা, জেলা)_",
        parse_mode="Markdown")
    return ADDRESS


async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ok, result = validate_address(update.message.text)
    if not ok:
        await update.message.reply_text(result, parse_mode="Markdown")
        return ADDRESS
    context.user_data["checkout"]["address"] = result
    await update.message.reply_text(
        f"✅ ঠিকানা সংরক্ষিত!\n\n━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 *ধাপ ৫/৬ — বিশেষ নির্দেশনা (ঐচ্ছিক):*\n_(রং, সাইজ ইত্যাদি — না থাকলে *skip* লিখুন)_",
        parse_mode="Markdown")
    return NOTES


async def get_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text.strip()
    context.user_data["checkout"]["notes"] = None if txt.lower() in ("skip", "না", "") else txt

    # Now show payment methods — step 6
    methods = get_payment_methods(active_only=True)
    co      = context.user_data["checkout"]
    # Filter COD if not allowed
    if not co.get("cod_allowed", True):
        methods = [m for m in methods if not _g(m, "is_cod")]

    if not methods:
        await update.message.reply_text("⚠️ কোনো পেমেন্ট পদ্ধতি নেই। Admin কে জানান।")
        return ConversationHandler.END

    items    = co["items"]
    subtotal = sum(i["unit_price"] * i["quantity"] for i in items)
    delivery = co.get("delivery_charge", 0)
    discount = co.get("discount", 0)
    total    = subtotal + delivery - discount

    co["subtotal"]    = round(subtotal, 2)
    co["total_price"] = round(total, 2)

    items_lines = "\n".join(
        f"  • {i['product_name'][:24]} × {i['quantity']} = {format_price(i['unit_price'] * i['quantity'])}"
        for i in items
    )
    disc_line  = f"\n🎫 ডিসকাউন্ট: -{format_price(discount)}" if discount else ""
    notes_line = f"\n📝 নোট: {co.get('notes')}" if co.get("notes") else ""

    summary = (
        f"💳 *ধাপ ৬/৬ — পেমেন্ট পদ্ধতি*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 *পণ্য:*\n{items_lines}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 {co['full_name']} | 📞 {co['phone']}\n"
        f"📍 {co['address']}"
        f"{notes_line}\n"
        f"🚚 {co.get('delivery_method','—')} | ৳{int(delivery)}"
        f"{disc_line}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 *মোট: {format_price(total)}*\n\n"
        f"পেমেন্ট পদ্ধতি বেছে নিন:"
    )
    # Use a temp order_id placeholder (0) — actual order created after confirm
    buttons = []
    for m in methods:
        emoji = _g(m, "emoji", "💳")
        name  = _g(m, "name", "পেমেন্ট")
        mid   = _g(m, "method_id", 0)
        buttons.append([InlineKeyboardButton(f"{emoji} {name}", callback_data=f"pmselect_{mid}")])
    buttons.append([InlineKeyboardButton("❌ বাতিল", callback_data="cancel_checkout")])

    await update.message.reply_text(summary, parse_mode="Markdown",
                                    reply_markup=InlineKeyboardMarkup(buttons))
    return PAYMENT


async def get_payment_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User selects payment method — then show final confirm."""
    query     = update.callback_query
    await safe_answer(query)
    method_id = int(query.data.split("_")[1])

    from database.queries import get_payment_method
    method = get_payment_method(method_id)
    if not method:
        await query.answer("❌ পাওয়া যায়নি!", show_alert=True)
        return PAYMENT

    co = context.user_data["checkout"]
    co["payment_method"]    = _g(method, "name")
    co["payment_method_id"] = method_id
    co["is_cod"]            = bool(_g(method, "is_cod"))

    emoji = _g(method, "emoji", "💳")
    name  = _g(method, "name", "পেমেন্ট")

    await safe_edit(query,
        f"✅ পেমেন্ট: *{emoji} {name}*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 *মোট: {format_price(co['total_price'])}*\n\n"
        f"অর্ডার নিশ্চিত করুন:",
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
        user_id=user_id,
        full_name=co["full_name"],
        phone=co["phone"],
        address=co["address"],
        delivery_method=co.get("delivery_method", "—"),
        delivery_charge=co.get("delivery_charge", 0),
        subtotal=co["subtotal"],
        total_price=co["total_price"],
        payment_method=co.get("payment_method", "pending"),
        advance_amount=co.get("advance_amount", 0),
        coupon_code=co.get("coupon_code"),
        discount=co.get("discount", 0),
        notes=co.get("notes"),
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

    items_summary = ", ".join(f"{i['product_name'][:12]} ×{i['quantity']}" for i in items)
    context.user_data["last_order_id"] = order_id
    context.user_data.pop("checkout", None)

    is_cod = co.get("is_cod", False)

    if is_cod:
        # COD — no payment screenshot needed
        await safe_edit(query,
            f"🎉 *অর্ডার সফলভাবে দেওয়া হয়েছে!*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 *Order ID:* `#{order_id}`\n"
            f"📦 *পণ্য:* {items_summary}\n"
            f"💰 *মোট:* {format_price(co['total_price'])}\n"
            f"💵 *পেমেন্ট:* ক্যাশ অন ডেলিভারি\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"✅ পণ্য পাওয়ার সময় পেমেন্ট করুন।\n"
            f"আমাদের ডেলিভারি টিম যোগাযোগ করবে! 🚚",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 আমার অর্ডার", callback_data="my_orders")],
                [InlineKeyboardButton("🏠 মেইন মেনু",   callback_data="main_menu")],
            ]))
    else:
        await safe_edit(query,
            f"🎉 *অর্ডার নিশ্চিত হয়েছে!*\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 *Order ID:* `#{order_id}`\n"
            f"📦 *পণ্য:* {items_summary}\n"
            f"💰 *মোট:* {format_price(co['total_price'])}\n"
            f"💳 *পেমেন্ট:* {co.get('payment_method','—')}\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"👇 এখন পেমেন্ট করুন ও স্ক্রিনশট আপলোড করুন:",
            reply_markup=order_placed_keyboard(order_id))

    admin_text = format_admin_new_order(order_id, {
        "full_name": co["full_name"], "phone": co["phone"],
        "address": co["address"], "delivery_method": co.get("delivery_method"),
        "items_summary": items_summary, "total_price": co["total_price"],
        "payment_method": co.get("payment_method", "—"), "user_id": user_id,
    })
    await notify_admins(context, admin_text, parse_mode="Markdown")
    return ConversationHandler.END


async def cancel_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("checkout", None)
    if update.callback_query:
        await safe_answer(update.callback_query)
        await safe_edit(update.callback_query, "❌ *চেকআউট বাতিল হয়েছে।*",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 মেইন মেনু", callback_data="main_menu")]]))
    elif update.message:
        await update.message.reply_text("❌ বাতিল। /start দিন।")
    return ConversationHandler.END


async def coupon_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    await safe_edit(query,
        "🎫 *কুপন কোড*\n\nআপনার কুপন কোড লিখুন:\n_(যেমন: PICKDEAL10)_",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data="main_menu")]]))
    return COUPON_INPUT


async def apply_coupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    from database.queries import get_cart_items
    code     = update.message.text.strip().upper()
    user_id  = update.effective_user.id
    items    = get_cart_items(user_id)
    subtotal = sum(float(_g(i, "discount_price") or _g(i, "price", 0)) * int(_g(i, "quantity", 1)) for i in items)
    coupon   = validate_coupon(code, subtotal)
    if not coupon:
        await update.message.reply_text(
            f"❌ কুপন `{code}` অবৈধ বা মেয়াদ শেষ!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 মেইন মেনু", callback_data="main_menu")]]))
        return ConversationHandler.END
    discount = calculate_coupon_discount(coupon, subtotal)
    if "checkout" not in context.user_data:
        context.user_data["checkout"] = {}
    context.user_data["checkout"]["coupon_code"] = code
    context.user_data["checkout"]["discount"]    = discount
    await update.message.reply_text(
        f"✅ *কুপন '{code}' প্রয়োগ হয়েছে!*\n\n"
        f"💰 সাবটোটাল: {format_price(subtotal)}\n"
        f"🎫 ডিসকাউন্ট: -{format_price(discount)}\n"
        f"💵 পরে: *{format_price(subtotal - discount)}*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛒 চেকআউট", callback_data="checkout")],
            [InlineKeyboardButton("🏠 মেইন মেনু", callback_data="main_menu")],
        ]))
    return ConversationHandler.END
