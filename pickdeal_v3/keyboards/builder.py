"""
keyboards/builder.py — PickDeal BD v3
All InlineKeyboardMarkup builders.
FIX: category callback uses ID not name → no more parse bugs.
FIX: product list pagination uses category_id not name string.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


# ════════════════════════════════════════════════
# MAIN MENU
# ════════════════════════════════════════════════

def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍️ পণ্য দেখুন",     callback_data="browse_categories"),
         InlineKeyboardButton("🔥 ফিচার্ড",         callback_data="featured_products")],
        [InlineKeyboardButton("🛒 আমার কার্ট",      callback_data="view_cart"),
         InlineKeyboardButton("❤️ উইশলিস্ট",        callback_data="my_wishlist")],
        [InlineKeyboardButton("📋 আমার অর্ডার",     callback_data="my_orders"),
         InlineKeyboardButton("🔍 অর্ডার ট্র্যাক", callback_data="track_order")],
        [InlineKeyboardButton("🔎 সার্চ",           callback_data="search_products"),
         InlineKeyboardButton("🎫 কুপন",            callback_data="use_coupon")],
        [InlineKeyboardButton("👤 প্রোফাইল",        callback_data="my_profile"),
         InlineKeyboardButton("💬 সাপোর্ট",         callback_data="support")],
    ])


def back_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🏠 মেইন মেনু", callback_data="main_menu")
    ]])


def back_button(cb: str, label: str = "⬅️ ফিরে যান") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=cb)]])


# ════════════════════════════════════════════════
# CATEGORIES  (FIX: uses category_id in callback)
# ════════════════════════════════════════════════

def categories_keyboard(categories: list) -> InlineKeyboardMarkup:
    """
    BUG FIX: Old code used category name in callback_data.
    If name contained '_', show_products parser broke.
    New: callback = catid_<id>, handler reads ID then fetches name from DB.
    """
    buttons = []
    row = []
    for i, cat in enumerate(categories):
        emoji = cat["emoji"] if "emoji" in cat.keys() else "🛍️"
        count = cat["product_count"] if "product_count" in cat.keys() else ""
        label = f"{emoji} {cat['name']}" + (f" ({count})" if count else "")
        row.append(InlineKeyboardButton(label, callback_data=f"catid_{cat['category_id']}"))
        if len(row) == 2 or i == len(categories) - 1:
            buttons.append(row)
            row = []
    buttons.append([
        InlineKeyboardButton("🌟 ফিচার্ড",    callback_data="featured_products"),
        InlineKeyboardButton("🔥 বেস্টসেলার", callback_data="bestseller_products"),
    ])
    buttons.append([
        InlineKeyboardButton("✨ নতুন পণ্য",   callback_data="new_arrivals"),
        InlineKeyboardButton("🏠 মেইন মেনু",   callback_data="main_menu"),
    ])
    return InlineKeyboardMarkup(buttons)


def product_list_keyboard(products: list, category_id: int, page: int,
                           total: int, per_page: int = 6) -> InlineKeyboardMarkup:
    """FIX: Uses category_id in pagination callbacks, not category name."""
    buttons = []
    for p in products:
        stock_icon = "✅" if p["stock"] > 0 else "❌"
        price = p["discount_price"] or p["price"]
        label = f"{stock_icon} {p['name'][:24]} — ৳{int(float(price)):,}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"product_{p['product_id']}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ আগে", callback_data=f"catid_{category_id}_p{page-1}"))
    total_pages = max(1, (total + per_page - 1) // per_page)
    if total_pages > 1:
        nav.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="noop"))
    if (page + 1) * per_page < total:
        nav.append(InlineKeyboardButton("পরে ➡️", callback_data=f"catid_{category_id}_p{page+1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton("⬅️ ক্যাটাগরি", callback_data="browse_categories")])
    return InlineKeyboardMarkup(buttons)


def product_detail_keyboard(product_id: int, category_id: int,
                             in_stock: bool, in_wishlist: bool) -> InlineKeyboardMarkup:
    buttons = []
    if in_stock:
        buttons.append([
            InlineKeyboardButton("🛒 কার্টে যোগ",  callback_data=f"addcart_{product_id}"),
            InlineKeyboardButton("⚡ এখনই কিনুন",  callback_data=f"buynow_{product_id}"),
        ])
    else:
        buttons.append([InlineKeyboardButton("❌ স্টক নেই", callback_data="noop")])

    wish_label = "💔 উইশলিস্ট থেকে বাদ" if in_wishlist else "❤️ উইশলিস্টে যোগ"
    buttons.append([
        InlineKeyboardButton(wish_label,             callback_data=f"wish_{product_id}"),
        InlineKeyboardButton("📤 শেয়ার করুন",      callback_data=f"share_{product_id}"),
    ])
    buttons.append([InlineKeyboardButton("⬅️ ফিরে যান", callback_data=f"catid_{category_id}")])
    return InlineKeyboardMarkup(buttons)


def featured_products_keyboard(products: list, back_cb: str = "browse_categories") -> InlineKeyboardMarkup:
    buttons = []
    for p in products:
        price = p["discount_price"] or p["price"]
        label = f"⭐ {p['name'][:26]} — ৳{int(float(price)):,}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"product_{p['product_id']}")])
    buttons.append([InlineKeyboardButton("🛍️ সব ক্যাটাগরি", callback_data="browse_categories")])
    buttons.append([InlineKeyboardButton("🏠 মেইন মেনু",    callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


# ════════════════════════════════════════════════
# CART
# ════════════════════════════════════════════════

def cart_keyboard(items: list) -> InlineKeyboardMarkup:
    buttons = []
    for item in items:
        name = item["name"][:18]
        buttons.append([
            InlineKeyboardButton("➖", callback_data=f"cartqty_{item['product_id']}_dec"),
            InlineKeyboardButton(f"{name} ×{item['quantity']}", callback_data="noop"),
            InlineKeyboardButton("➕", callback_data=f"cartqty_{item['product_id']}_inc"),
            InlineKeyboardButton("🗑️", callback_data=f"cartdel_{item['product_id']}"),
        ])
    buttons.append([
        InlineKeyboardButton("🛒 চেকআউট",        callback_data="checkout"),
        InlineKeyboardButton("🗑️ কার্ট খালি",   callback_data="clear_cart"),
    ])
    buttons.append([InlineKeyboardButton("🛍️ কেনাকাটা চালিয়ে যান", callback_data="browse_categories")])
    buttons.append([InlineKeyboardButton("🏠 মেইন মেনু", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def empty_cart_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍️ পণ্য দেখুন", callback_data="browse_categories")],
        [InlineKeyboardButton("🏠 মেইন মেনু",   callback_data="main_menu")],
    ])


# ════════════════════════════════════════════════
# CHECKOUT — DELIVERY (dynamic from DB)
# ════════════════════════════════════════════════

def delivery_methods_keyboard(methods: list) -> InlineKeyboardMarkup:
    """Dynamic delivery method selection from DB."""
    buttons = []
    for m in methods:
        charge_str = f"৳{int(m['charge'])}" if m["charge"] > 0 else "বিনামূল্যে"
        cod_str = " • COD ✅" if m["cod_allowed"] else " • COD ❌"
        label = f"🚚 {m['name']} ({charge_str}){cod_str}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"dlv_{m['method_id']}")])
    buttons.append([InlineKeyboardButton("❌ বাতিল", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def payment_methods_keyboard(methods: list, order_id: int) -> InlineKeyboardMarkup:
    """Dynamic payment method selection from DB."""
    buttons = []
    for m in methods:
        label = f"{m['emoji']} {m['name']}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"pay_{order_id}_{m['method_id']}")])
    buttons.append([InlineKeyboardButton("❌ বাতিল", callback_data="my_orders")])
    return InlineKeyboardMarkup(buttons)


def order_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ অর্ডার নিশ্চিত", callback_data="confirm_order"),
        InlineKeyboardButton("❌ বাতিল",           callback_data="cancel_checkout"),
    ]])


def order_placed_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 পেমেন্ট করুন",  callback_data=f"payorder_{order_id}")],
        [InlineKeyboardButton("📋 আমার অর্ডার",   callback_data="my_orders")],
        [InlineKeyboardButton("🏠 মেইন মেনু",     callback_data="main_menu")],
    ])


# ════════════════════════════════════════════════
# ORDER / TRACKING
# ════════════════════════════════════════════════

def order_list_keyboard(orders: list) -> InlineKeyboardMarkup:
    buttons = []
    for o in orders:
        from utils.formatters import short_status
        st    = short_status(o["status"])
        label = f"#{o['order_id']} | {st} | ৳{int(float(o['total_price'])):,}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"vieworder_{o['order_id']}")])
    buttons.append([InlineKeyboardButton("🏠 মেইন মেনু", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def order_detail_keyboard(order_id: int, status: str) -> InlineKeyboardMarkup:
    buttons = []
    if status in ("pending", "awaiting_payment"):
        buttons.append([InlineKeyboardButton("💳 পেমেন্ট করুন", callback_data=f"payorder_{order_id}")])
    buttons.append([
        InlineKeyboardButton("📋 সব অর্ডার", callback_data="my_orders"),
        InlineKeyboardButton("🏠 মেনু",      callback_data="main_menu"),
    ])
    return InlineKeyboardMarkup(buttons)


# ════════════════════════════════════════════════
# PROFILE / WISHLIST / SUPPORT
# ════════════════════════════════════════════════

def profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 আমার অর্ডার",    callback_data="my_orders"),
         InlineKeyboardButton("❤️ উইশলিস্ট",       callback_data="my_wishlist")],
        [InlineKeyboardButton("🕐 সম্প্রতি দেখা",  callback_data="recently_viewed"),
         InlineKeyboardButton("🎫 কুপন",            callback_data="use_coupon")],
        [InlineKeyboardButton("🏠 মেইন মেনু",      callback_data="main_menu")],
    ])


def wishlist_keyboard(products: list) -> InlineKeyboardMarkup:
    buttons = []
    for p in products:
        price = p["discount_price"] or p["price"]
        buttons.append([
            InlineKeyboardButton(f"🛍️ {p['name'][:20]}", callback_data=f"product_{p['product_id']}"),
            InlineKeyboardButton("💔 সরান",               callback_data=f"wish_{p['product_id']}"),
        ])
    buttons.append([InlineKeyboardButton("🏠 মেইন মেনু", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def support_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎫 নতুন টিকেট",   callback_data="new_ticket")],
        [InlineKeyboardButton("📋 আমার টিকেট",   callback_data="my_tickets")],
        [InlineKeyboardButton("🏠 মেইন মেনু",    callback_data="main_menu")],
    ])


# ════════════════════════════════════════════════
# ADMIN KEYBOARDS
# ════════════════════════════════════════════════

def admin_dashboard_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 সব অর্ডার",    callback_data="adm_orders_all_0"),
         InlineKeyboardButton("🕐 পেন্ডিং",      callback_data="adm_orders_pending_0")],
        [InlineKeyboardButton("✅ কনফার্ম",       callback_data="adm_orders_confirmed_0"),
         InlineKeyboardButton("🚚 শিপড",          callback_data="adm_orders_shipped_0")],
        [InlineKeyboardButton("📦 পণ্য যোগ",      callback_data="adm_add_product"),
         InlineKeyboardButton("📝 পণ্য লিস্ট",   callback_data="adm_products_0")],
        [InlineKeyboardButton("🏷️ ক্যাটাগরি",   callback_data="adm_categories"),
         InlineKeyboardButton("🚚 ডেলিভারি",     callback_data="adm_delivery")],
        [InlineKeyboardButton("💳 পেমেন্ট",       callback_data="adm_payment_methods"),
         InlineKeyboardButton("🎫 কুপন",          callback_data="adm_coupons")],
        [InlineKeyboardButton("📊 Analytics",     callback_data="adm_analytics"),
         InlineKeyboardButton("👥 কাস্টমার",      callback_data="adm_customers")],
        [InlineKeyboardButton("🎫 টিকেট",         callback_data="adm_tickets_0"),
         InlineKeyboardButton("📢 ব্রডকাস্ট",    callback_data="adm_broadcast")],
        [InlineKeyboardButton("⚠️ কম স্টক",      callback_data="adm_low_stock"),
         InlineKeyboardButton("✉️ ইউজার মেসেজ",  callback_data="adm_msg_user")],
    ])


def admin_order_actions_keyboard(order_id: int, status: str) -> InlineKeyboardMarkup:
    FLOW = {
        "pending":           [("✅ পেমেন্ট নিশ্চিত", "confirmed"), ("❌ বাতিল", "cancelled")],
        "awaiting_payment":  [("✅ পেমেন্ট নিশ্চিত", "confirmed"), ("❌ বাতিল", "cancelled")],
        "confirmed":         [("⚙️ প্রসেসিং",        "processing"), ("❌ বাতিল", "cancelled")],
        "processing":        [("📦 প্যাক করা হয়েছে","packed"),    ("❌ বাতিল", "cancelled")],
        "packed":            [("🚚 শিপ করুন",         "shipped")],
        "shipped":           [("🛵 ডেলিভারিতে",      "out_for_delivery")],
        "out_for_delivery":  [("🎉 ডেলিভারি সম্পন্ন","delivered")],
        "delivered":         [("↩️ রিফান্ড",          "refunded")],
        "cancelled":         [],
        "refunded":          [],
    }
    buttons = []
    for label, new_status in FLOW.get(status, []):
        buttons.append([InlineKeyboardButton(label, callback_data=f"admupd_{order_id}_{new_status}")])
    buttons.append([
        InlineKeyboardButton("📝 নোট যোগ",   callback_data=f"adm_order_note_{order_id}"),
        InlineKeyboardButton("⬅️ অর্ডার",   callback_data="adm_orders_all_0"),
    ])
    return InlineKeyboardMarkup(buttons)


def admin_product_keyboard(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ নাম",           callback_data=f"admprod_name_{product_id}"),
         InlineKeyboardButton("💰 মূল্য",          callback_data=f"admprod_price_{product_id}")],
        [InlineKeyboardButton("🔖 ডিসকাউন্ট",    callback_data=f"admprod_discount_{product_id}"),
         InlineKeyboardButton("📦 স্টক",           callback_data=f"admprod_stock_{product_id}")],
        [InlineKeyboardButton("🖼️ ছবি সেট",       callback_data=f"admprod_image_{product_id}"),
         InlineKeyboardButton("📝 বিবরণ",          callback_data=f"admprod_desc_{product_id}")],
        [InlineKeyboardButton("🏷️ ট্যাগ",         callback_data=f"admprod_tags_{product_id}"),
         InlineKeyboardButton("⭐ ফিচার্ড",        callback_data=f"admprod_featured_{product_id}")],
        [InlineKeyboardButton("🗑️ ডিলিট",         callback_data=f"admprod_delete_{product_id}")],
        [InlineKeyboardButton("⬅️ পণ্য লিস্ট",   callback_data="adm_products_0")],
    ])


def admin_products_list_keyboard(products: list, page: int, has_more: bool) -> InlineKeyboardMarkup:
    buttons = []
    for p in products:
        st    = "✅" if p["is_active"] else "❌"
        label = f"{st} {p['name'][:22]} | ৳{int(float(p['price'])):,} | {p['stock']}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"admprodview_{p['product_id']}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ আগে", callback_data=f"adm_products_{page-1}"))
    if has_more:
        nav.append(InlineKeyboardButton("পরে ➡️", callback_data=f"adm_products_{page+1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("⬅️ Dashboard", callback_data="adm_panel")])
    return InlineKeyboardMarkup(buttons)


def admin_categories_keyboard(categories: list) -> InlineKeyboardMarkup:
    buttons = []
    for cat in categories:
        st    = "✅" if cat["is_active"] else "❌"
        label = f"{st} {cat['emoji']} {cat['name']} ({cat.get('product_count', 0)})"
        buttons.append([InlineKeyboardButton(label, callback_data=f"adm_cat_view_{cat['category_id']}")])
    buttons.append([InlineKeyboardButton("➕ নতুন ক্যাটাগরি", callback_data="adm_cat_add")])
    buttons.append([InlineKeyboardButton("⬅️ Dashboard",       callback_data="adm_panel")])
    return InlineKeyboardMarkup(buttons)


def admin_category_detail_keyboard(cat_id: int, is_active: bool, is_featured: bool) -> InlineKeyboardMarkup:
    toggle_label   = "🙈 লুকান"      if is_active  else "👁️ দেখান"
    featured_label = "⭐ আন-ফিচার"  if is_featured else "⭐ ফিচার করুন"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ নাম পরিবর্তন",  callback_data=f"adm_cat_edit_name_{cat_id}"),
         InlineKeyboardButton("😊 Emoji পরিবর্তন", callback_data=f"adm_cat_edit_emoji_{cat_id}")],
        [InlineKeyboardButton(toggle_label,          callback_data=f"adm_cat_toggle_{cat_id}"),
         InlineKeyboardButton(featured_label,        callback_data=f"adm_cat_feature_{cat_id}")],
        [InlineKeyboardButton("🗑️ ডিলিট",          callback_data=f"adm_cat_delete_{cat_id}")],
        [InlineKeyboardButton("⬅️ ক্যাটাগরি",     callback_data="adm_categories")],
    ])


def admin_delivery_keyboard(methods: list) -> InlineKeyboardMarkup:
    buttons = []
    for m in methods:
        st    = "✅" if m["is_active"] else "❌"
        cod   = "COD✓" if m["cod_allowed"] else "COD✗"
        label = f"{st} {m['name']} | ৳{int(m['charge'])} | {cod}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"adm_dlv_view_{m['method_id']}")])
    buttons.append([InlineKeyboardButton("➕ নতুন ডেলিভারি পদ্ধতি", callback_data="adm_dlv_add")])
    buttons.append([InlineKeyboardButton("⬅️ Dashboard",             callback_data="adm_panel")])
    return InlineKeyboardMarkup(buttons)


def admin_delivery_detail_keyboard(method_id: int, is_active: bool) -> InlineKeyboardMarkup:
    toggle = "🙈 বন্ধ করুন" if is_active else "✅ চালু করুন"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ নাম",      callback_data=f"adm_dlv_edit_name_{method_id}"),
         InlineKeyboardButton("💰 চার্জ",   callback_data=f"adm_dlv_edit_charge_{method_id}")],
        [InlineKeyboardButton(toggle,         callback_data=f"adm_dlv_toggle_{method_id}"),
         InlineKeyboardButton("🗑️ ডিলিট",  callback_data=f"adm_dlv_delete_{method_id}")],
        [InlineKeyboardButton("⬅️ ডেলিভারি", callback_data="adm_delivery")],
    ])


def admin_payment_methods_keyboard(methods: list) -> InlineKeyboardMarkup:
    buttons = []
    for m in methods:
        st    = "✅" if m["is_active"] else "❌"
        label = f"{st} {m['emoji']} {m['name']} | {m['number'] or 'COD'}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"adm_pm_view_{m['method_id']}")])
    buttons.append([InlineKeyboardButton("➕ নতুন পদ্ধতি", callback_data="adm_pm_add")])
    buttons.append([InlineKeyboardButton("⬅️ Dashboard",    callback_data="adm_panel")])
    return InlineKeyboardMarkup(buttons)


def admin_payment_detail_keyboard(method_id: int, is_active: bool) -> InlineKeyboardMarkup:
    toggle = "🙈 বন্ধ করুন" if is_active else "✅ চালু করুন"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ নাম",       callback_data=f"adm_pm_edit_name_{method_id}"),
         InlineKeyboardButton("📱 নম্বর",    callback_data=f"adm_pm_edit_number_{method_id}")],
        [InlineKeyboardButton(toggle,          callback_data=f"adm_pm_toggle_{method_id}")],
        [InlineKeyboardButton("⬅️ পেমেন্ট",  callback_data="adm_payment_methods")],
    ])


def admin_coupons_keyboard(coupons: list) -> InlineKeyboardMarkup:
    buttons = []
    for c in coupons:
        st   = "✅" if c["is_active"] else "❌"
        disc = f"{c['discount_val']}%" if c["discount_type"] == "percent" else f"৳{int(c['discount_val'])}"
        label = f"{st} {c['code']} | {disc} | {c['used_count']}/{c['max_uses']}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"adm_coupon_view_{c['coupon_id']}")])
    buttons.append([InlineKeyboardButton("➕ নতুন কুপন", callback_data="adm_coupon_add")])
    buttons.append([InlineKeyboardButton("⬅️ Dashboard", callback_data="adm_panel")])
    return InlineKeyboardMarkup(buttons)


def admin_coupon_detail_keyboard(coupon_id: int, is_active: bool) -> InlineKeyboardMarkup:
    toggle = "🙈 নিষ্ক্রিয়" if is_active else "✅ সক্রিয়"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ কোড",      callback_data=f"adm_coupon_edit_code_{coupon_id}"),
         InlineKeyboardButton("💰 ডিসকাউন্ট",callback_data=f"adm_coupon_edit_val_{coupon_id}")],
        [InlineKeyboardButton("📅 মেয়াদ",   callback_data=f"adm_coupon_edit_exp_{coupon_id}"),
         InlineKeyboardButton(toggle,         callback_data=f"adm_coupon_toggle_{coupon_id}")],
        [InlineKeyboardButton("🗑️ ডিলিট",  callback_data=f"adm_coupon_delete_{coupon_id}")],
        [InlineKeyboardButton("⬅️ কুপন",    callback_data="adm_coupons")],
    ])


def admin_ticket_keyboard(ticket_id: int, status: str) -> InlineKeyboardMarkup:
    buttons = []
    if status in ("open", "in_progress"):
        buttons.append([
            InlineKeyboardButton("💬 রিপ্লাই দিন", callback_data=f"adm_ticket_reply_{ticket_id}"),
            InlineKeyboardButton("✅ বন্ধ করুন",   callback_data=f"adm_ticket_close_{ticket_id}"),
        ])
    else:
        buttons.append([
            InlineKeyboardButton("🔄 পুনরায় খুলুন", callback_data=f"adm_ticket_reopen_{ticket_id}")
        ])
    buttons.append([InlineKeyboardButton("⬅️ টিকেট", callback_data="adm_tickets_0")])
    return InlineKeyboardMarkup(buttons)
