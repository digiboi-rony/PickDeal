"""keyboards/admin_kb.py"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from models.order import STATUS_FLOW, STATUS_LABEL, STATUS_EMOJI
from config.settings import ORDERS_PER_PAGE


def admin_dashboard_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 সব অর্ডার",      callback_data="adm_orders_all_0"),
         InlineKeyboardButton("🕐 পেন্ডিং",        callback_data="adm_orders_pending_0")],
        [InlineKeyboardButton("📦 পণ্য লিস্ট",     callback_data="adm_products_0"),
         InlineKeyboardButton("➕ পণ্য যোগ করুন", callback_data="adm_add_product")],
        [InlineKeyboardButton("📊 অ্যানালিটিক্স",  callback_data="adm_analytics"),
         InlineKeyboardButton("📢 ব্রডকাস্ট",      callback_data="adm_broadcast")],
        [InlineKeyboardButton("🎫 কুপন",            callback_data="adm_coupons"),
         InlineKeyboardButton("👥 কাস্টমার",        callback_data="adm_customers")],
    ])


def orders_list_kb(orders, status, page) -> InlineKeyboardMarkup:
    buttons = []
    for o in orders:
        em = STATUS_EMOJI.get(o["status"], "❓")
        label = f"#{o['order_id']} {em} {o['first_name'][:10]} ৳{o['total']:,.0f}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"adm_order_{o['order_id']}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"adm_orders_{status}_{page-1}"))
    if len(orders) == ORDERS_PER_PAGE:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"adm_orders_{status}_{page+1}"))
    if nav:
        buttons.append(nav)

    # Quick filter buttons
    buttons.append([
        InlineKeyboardButton("🕐 Pending",  callback_data="adm_orders_pending_0"),
        InlineKeyboardButton("✅ Confirmed", callback_data="adm_orders_payment_confirmed_0"),
        InlineKeyboardButton("🚚 Shipping",  callback_data="adm_orders_shipping_0"),
    ])
    buttons.append([InlineKeyboardButton("⬅️ Dashboard", callback_data="adm_dashboard")])
    return InlineKeyboardMarkup(buttons)


def order_action_kb(order_id, current_status) -> InlineKeyboardMarkup:
    next_statuses = STATUS_FLOW.get(current_status, [])
    buttons = []
    for ns in next_statuses:
        em = STATUS_EMOJI.get(ns, "")
        buttons.append([InlineKeyboardButton(
            f"{em} {STATUS_LABEL.get(ns, ns)}",
            callback_data=f"adm_upd_{order_id}_{ns}"
        )])
    buttons.append([InlineKeyboardButton("⬅️ অর্ডার লিস্ট", callback_data="adm_orders_all_0")])
    return InlineKeyboardMarkup(buttons)


def product_list_kb(products, page) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(
            f"{'⭐' if p['is_featured'] else '📦'} {p['name'][:25]} (স্টক: {p['stock']})",
            callback_data=f"adm_product_{p['product_id']}"
        )]
        for p in products
    ]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"adm_products_{page-1}"))
    if len(products) >= 8:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"adm_products_{page+1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("⬅️ Dashboard", callback_data="adm_dashboard")])
    return InlineKeyboardMarkup(buttons)


def product_action_kb(product_id) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ নাম পরিবর্তন",     callback_data=f"adm_pedit_{product_id}_name"),
         InlineKeyboardButton("💰 মূল্য পরিবর্তন",   callback_data=f"adm_pedit_{product_id}_price")],
        [InlineKeyboardButton("📦 স্টক আপডেট",       callback_data=f"adm_pedit_{product_id}_stock"),
         InlineKeyboardButton("🏷️ ডিসকাউন্ট",       callback_data=f"adm_pedit_{product_id}_discount_price")],
        [InlineKeyboardButton("⭐ Featured টগল",     callback_data=f"adm_pfeat_{product_id}"),
         InlineKeyboardButton("🖼️ ছবি যোগ করুন",    callback_data=f"adm_pimg_{product_id}")],
        [InlineKeyboardButton("🗑️ মুছে ফেলুন",       callback_data=f"adm_pdel_{product_id}")],
        [InlineKeyboardButton("⬅️ পণ্য লিস্ট",       callback_data="adm_products_0")],
    ])
