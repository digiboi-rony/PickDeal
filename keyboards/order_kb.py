"""keyboards/order_kb.py"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config.settings import COD_AVAILABLE


def cart_kb(items) -> InlineKeyboardMarkup:
    """Keyboard shown with cart view."""
    buttons = []
    for it in items:
        qty = it["quantity"]
        pid = it["product_id"]
        buttons.append([
            InlineKeyboardButton(f"➖", callback_data=f"qty_dec_{pid}"),
            InlineKeyboardButton(f"{it['name'][:18]} ({qty})", callback_data="noop"),
            InlineKeyboardButton(f"➕", callback_data=f"qty_inc_{pid}"),
            InlineKeyboardButton("🗑️", callback_data=f"remove_{pid}"),
        ])
    buttons += [
        [InlineKeyboardButton("🧹 কার্ট খালি করুন",  callback_data="clear_cart")],
        [InlineKeyboardButton("✅ চেকআউট করুন",      callback_data="checkout"),
         InlineKeyboardButton("⬅️ মেনু",             callback_data="main_menu")],
    ]
    return InlineKeyboardMarkup(buttons)


def payment_method_kb(order_id) -> InlineKeyboardMarkup:
    btns = [
        [InlineKeyboardButton("📱 bKash",  callback_data=f"pay_{order_id}_bkash")],
        [InlineKeyboardButton("📱 Nagad",  callback_data=f"pay_{order_id}_nagad")],
    ]
    if COD_AVAILABLE:
        btns.append([InlineKeyboardButton("💵 Cash on Delivery", callback_data=f"pay_{order_id}_cod")])
    btns.append([InlineKeyboardButton("❌ বাতিল", callback_data="main_menu")])
    return InlineKeyboardMarkup(btns)


def upload_screenshot_kb(order_id) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ বাতিল", callback_data="main_menu")
    ]])


def my_orders_kb(orders) -> InlineKeyboardMarkup:
    from models.order import STATUS_EMOJI
    buttons = []
    for o in orders:
        em    = STATUS_EMOJI.get(o["status"], "❓")
        label = f"#{o['order_id']} {em} ৳{o['total']:,.0f}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"order_detail_{o['order_id']}")])
    buttons.append([InlineKeyboardButton("⬅️ মেনু", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def order_detail_kb(order_id, status) -> InlineKeyboardMarkup:
    btns = []
    if status == "pending":
        btns.append([InlineKeyboardButton("💳 পেমেন্ট করুন",
                                          callback_data=f"choose_payment_{order_id}")])
    btns.append([InlineKeyboardButton("📍 ট্র্যাক করুন",   callback_data=f"track_{order_id}"),
                 InlineKeyboardButton("⬅️ পিছনে",           callback_data="my_orders")])
    return InlineKeyboardMarkup(btns)


def area_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏙️ ঢাকার ভেতরে",  callback_data="area_dhaka"),
         InlineKeyboardButton("🌍 ঢাকার বাইরে",  callback_data="area_outside")],
        [InlineKeyboardButton("❌ বাতিল",         callback_data="main_menu")],
    ])


def confirm_order_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ অর্ডার কনফার্ম করুন", callback_data="confirm_order")],
        [InlineKeyboardButton("🎫 কুপন প্রয়োগ করুন",  callback_data="apply_coupon"),
         InlineKeyboardButton("❌ বাতিল",              callback_data="main_menu")],
    ])
