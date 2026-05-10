"""
handlers/checkout.py
====================
Multi-step checkout ConversationHandler.
Flow: cart → name → phone → address → area → notes → coupon? → review → confirm
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

import models.cart as cart_model
import models.coupon as coupon_model
import models.order as order_model
from services.order_service import build_order_from_cart, place_order
from services.notification import notify_new_order, notify_admins
from keyboards.order_kb import (
    area_kb, confirm_order_kb, payment_method_kb
)
from utils.formatters import taka, cart_summary
from utils.validators import is_valid_name, is_valid_phone, is_valid_address, clean_phone
from config.settings import ADMIN_IDS

logger = logging.getLogger(__name__)

# ─── Conversation states ─────────────────────────────────────────────────────
(NAME, PHONE, ADDRESS, AREA, NOTES, COUPON_WAIT,
 REVIEW, PAYMENT_WAIT, SCREENSHOT_WAIT) = range(100, 109)


async def start_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Entry: callback 'checkout'"""
    query   = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    items = cart_model.get_items(user_id)
    if not items:
        await query.edit_message_text(
            "🛒 কার্ট খালি! আগে পণ্য যোগ করুন।",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🛍️ পণ্য দেখুন", callback_data="browse")
            ]])
        )
        return ConversationHandler.END

    context.user_data["checkout"] = {}

    await query.edit_message_text(
        f"{cart_summary(items)}\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "✅ চেকআউট শুরু হচ্ছে!\n\n"
        "*ধাপ ১/৫ — আপনার পুরো নাম লিখুন:*\n"
        "_(উদাহরণ: রহিম উদ্দিন)_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ বাতিল", callback_data="main_menu")
        ]])
    )
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    if not is_valid_name(name):
        await update.message.reply_text(
            "⚠️ নাম সঠিক নয়। কমপক্ষে ৩ অক্ষরের পুরো নাম দিন:"
        )
        return NAME
    context.user_data["checkout"]["full_name"] = name
    await update.message.reply_text(
        f"✅ নাম: *{name}*\n\n"
        "*ধাপ ২/৫ — মোবাইল নম্বর লিখুন:*\n"
        "_(উদাহরণ: 01712345678)_",
        parse_mode="Markdown",
    )
    return PHONE


async def get_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw = update.message.text
    phone = clean_phone(raw)
    if not is_valid_phone(phone):
        await update.message.reply_text(
            "⚠️ নম্বর সঠিক নয়। বাংলাদেশি মোবাইল নম্বর দিন:\n_(উদাহরণ: 01712345678)_",
            parse_mode="Markdown"
        )
        return PHONE
    context.user_data["checkout"]["phone"] = phone
    await update.message.reply_text(
        f"✅ ফোন: *{phone}*\n\n"
        "*ধাপ ৩/৫ — ডেলিভারি ঠিকানা লিখুন:*\n"
        "_(বাড়ি/ফ্ল্যাট নম্বর, রোড, এলাকা, থানা, জেলা)_",
        parse_mode="Markdown",
    )
    return ADDRESS


async def get_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
    address = update.message.text.strip()
    if not is_valid_address(address):
        await update.message.reply_text(
            "⚠️ ঠিকানা অনেক ছোট। পূর্ণ ডেলিভারি ঠিকানা দিন:"
        )
        return ADDRESS
    context.user_data["checkout"]["address"] = address
    await update.message.reply_text(
        f"✅ ঠিকানা সেভ হয়েছে!\n\n"
        "*ধাপ ৪/৫ — আপনি কোথায় থাকেন?*",
        parse_mode="Markdown",
        reply_markup=area_kb(),
    )
    return AREA


async def get_area(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    area  = "dhaka" if query.data == "area_dhaka" else "outside"
    context.user_data["checkout"]["area"] = area

    from config.settings import DELIVERY_CHARGE_DHAKA, DELIVERY_CHARGE_OUTSIDE
    fee = DELIVERY_CHARGE_DHAKA if area == "dhaka" else DELIVERY_CHARGE_OUTSIDE
    label = "ঢাকার ভেতরে" if area == "dhaka" else "ঢাকার বাইরে"

    await query.edit_message_text(
        f"✅ এলাকা: *{label}* (ডেলিভারি চার্জ: {taka(fee)})\n\n"
        "*ধাপ ৫/৫ — কোনো বিশেষ নির্দেশনা আছে?*\n"
        "_(না থাকলে 'না' বা 'skip' লিখুন)_",
        parse_mode="Markdown",
    )
    return NOTES


async def get_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    notes = update.message.text.strip()
    if notes.lower() in ("না", "na", "no", "skip", "-"):
        notes = ""
    context.user_data["checkout"]["notes"] = notes
    await update.message.reply_text(
        "🎫 *কুপন কোড আছে?*\n\nকোড লিখুন অথবা 'skip' করুন:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⏭️ Skip", callback_data="skip_coupon")
        ]])
    )
    return COUPON_WAIT


async def skip_coupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["checkout"]["coupon_code"] = None
    context.user_data["checkout"]["discount"]    = 0
    await _show_review(query, context)
    return REVIEW


async def apply_coupon_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User typed a coupon code."""
    code = update.message.text.strip().upper()
    user_id = update.effective_user.id

    financials = build_order_from_cart(user_id, context.user_data["checkout"])
    if not financials:
        return ConversationHandler.END

    coupon, err = coupon_model.validate(code, financials["subtotal"])
    if err:
        await update.message.reply_text(
            f"{err}\n\nআবার চেষ্টা করুন বা skip করুন:",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⏭️ Skip", callback_data="skip_coupon")
            ]])
        )
        return COUPON_WAIT

    discount = coupon_model.calc_discount(coupon, financials["subtotal"])
    context.user_data["checkout"]["coupon_code"] = code
    context.user_data["checkout"]["discount"]    = discount

    await update.message.reply_text(
        f"✅ কুপন প্রয়োগ হয়েছে! *{taka(discount)}* ছাড় পেয়েছেন 🎉",
        parse_mode="Markdown"
    )
    # show review inline
    await update.message.reply_text(
        "অর্ডার সারসংক্ষেপ লোড হচ্ছে...",
    )
    await _show_review_msg(update.message, context)
    return REVIEW


async def _show_review(query, context):
    """Edit message to show order review."""
    user_id    = query.from_user.id
    financials = build_order_from_cart(user_id, context.user_data["checkout"])
    sess       = context.user_data["checkout"]

    text = _review_text(sess, financials)
    await query.edit_message_text(
        text,
        parse_mode   = "Markdown",
        reply_markup = confirm_order_kb(),
    )


async def _show_review_msg(message, context):
    user_id    = message.from_user.id
    financials = build_order_from_cart(user_id, context.user_data["checkout"])
    sess       = context.user_data["checkout"]
    text       = _review_text(sess, financials)
    await message.reply_text(text, parse_mode="Markdown", reply_markup=confirm_order_kb())


def _review_text(sess, fin) -> str:
    coupon_line = ""
    if fin.get("coupon_code"):
        coupon_line = f"\n🎫 কুপন ({fin['coupon_code']}): -{taka(fin['discount'])}"

    item_lines = "\n".join(
        f"  • {it['name']} × {it['quantity']} = {taka(float(it['eff_price'])*it['quantity'])}"
        for it in fin["items"]
    )
    return (
        f"📋 *অর্ডার রিভিউ*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 নাম: {sess['full_name']}\n"
        f"📞 ফোন: {sess['phone']}\n"
        f"📍 ঠিকানা: {sess['address']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🛒 পণ্য:\n{item_lines}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 সাবটোটাল: {taka(fin['subtotal'])}\n"
        f"🚚 ডেলিভারি: {taka(fin['delivery'])}"
        f"{coupon_line}\n"
        f"💰 *মোট: {taka(fin['total'])}*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        "✅ নিশ্চিত করতে নিচের বাটন চাপুন:"
    )


async def confirm_order_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Place the order then show payment method selection."""
    query   = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    financials = build_order_from_cart(user_id, context.user_data["checkout"])
    if not financials:
        await query.edit_message_text("❌ কার্ট খালি হয়ে গেছে!")
        return ConversationHandler.END

    order_id = place_order(user_id, context.user_data["checkout"], financials)

    # Notify admins
    order = order_model.get(order_id)
    items = order_model.get_items(order_id)
    await notify_new_order(context.bot, ADMIN_IDS, order, items)

    context.user_data["checkout"]["order_id"] = order_id
    context.user_data.pop("checkout", None)

    await query.edit_message_text(
        f"🎉 *অর্ডার সফলভাবে দেওয়া হয়েছে!*\n\n"
        f"🆔 অর্ডার নম্বর: *#{order_id}*\n\n"
        f"💳 *এখন পেমেন্ট করুন:*\n"
        "নিচে পেমেন্ট পদ্ধতি বেছে নিন:",
        parse_mode   = "Markdown",
        reply_markup = payment_method_kb(order_id),
    )
    return ConversationHandler.END


async def cancel_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("checkout", None)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "❌ চেকআউট বাতিল হয়েছে।",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ মেনু", callback_data="main_menu")
            ]])
        )
    elif update.message:
        await update.message.reply_text("❌ চেকআউট বাতিল হয়েছে। /start দিয়ে শুরু করুন।")
    return ConversationHandler.END
