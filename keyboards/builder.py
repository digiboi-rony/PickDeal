"""
keyboards/builder.py
====================
All InlineKeyboardMarkup builders in one module.
Keeps handlers clean — no keyboard construction in handlers.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from config.settings import COD_ENABLED


# ═══════════════════════════════════════════════════════════════════
# MAIN MENU
# ═══════════════════════════════════════════════════════════════════

def main_menu_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍️ Shop Now",         callback_data="browse_products"),
         InlineKeyboardButton("🔥 Featured",          callback_data="featured_products")],
        [InlineKeyboardButton("🛒 My Cart",           callback_data="view_cart"),
         InlineKeyboardButton("❤️ Wishlist",          callback_data="my_wishlist")],
        [InlineKeyboardButton("📋 My Orders",         callback_data="my_orders"),
         InlineKeyboardButton("🔍 Track Order",       callback_data="track_order")],
        [InlineKeyboardButton("🔎 Search",            callback_data="search_products"),
         InlineKeyboardButton("🎫 Coupon",            callback_data="use_coupon")],
        [InlineKeyboardButton("👤 My Profile",        callback_data="my_profile"),
         InlineKeyboardButton("💬 Support",           callback_data="support")],
    ])


def back_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
    ]])


def back_button(callback: str, label: str = "⬅️ Back") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=callback)]])


# ═══════════════════════════════════════════════════════════════════
# PRODUCT KEYBOARDS
# ═══════════════════════════════════════════════════════════════════

def categories_keyboard(categories: list) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for i, cat in enumerate(categories):
        emoji = cat["emoji"] if "emoji" in cat.keys() else "🛍️"
        count = cat["product_count"] if "product_count" in cat.keys() else ""
        label = f"{emoji} {cat['name']}" + (f" ({count})" if count else "")
        row.append(InlineKeyboardButton(label, callback_data=f"cat_{cat['name']}"))
        if len(row) == 2 or i == len(categories) - 1:
            buttons.append(row)
            row = []
    buttons.append([
        InlineKeyboardButton("🔥 Featured",    callback_data="featured_products"),
        InlineKeyboardButton("⭐ Bestsellers", callback_data="bestseller_products"),
    ])
    buttons.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def product_list_keyboard(products: list, category: str, page: int, total: int,
                          per_page: int = 8) -> InlineKeyboardMarkup:
    buttons = []
    for p in products:
        stock_icon = "✅" if p["stock"] > 0 else "❌"
        price = p["discount_price"] or p["price"]
        label = f"{stock_icon} {p['name'][:25]} — ৳{int(price):,}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"product_{p['product_id']}")])

    # Pagination
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"cat_{category}_p{page-1}"))
    total_pages = (total + per_page - 1) // per_page
    if total_pages > 1:
        nav.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="noop"))
    if (page + 1) * per_page < total:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"cat_{category}_p{page+1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton("⬅️ Categories", callback_data="browse_products")])
    return InlineKeyboardMarkup(buttons)


def product_detail_keyboard(product_id: int, category: str, user_id: int,
                             in_stock: bool, in_wishlist: bool) -> InlineKeyboardMarkup:
    buttons = []
    if in_stock:
        buttons.append([
            InlineKeyboardButton("🛒 Add to Cart",  callback_data=f"addcart_{product_id}"),
            InlineKeyboardButton("⚡ Buy Now",       callback_data=f"order_{product_id}"),
        ])
    else:
        buttons.append([InlineKeyboardButton("❌ Out of Stock", callback_data="noop")])

    wish_label = "💔 Remove Wishlist" if in_wishlist else "❤️ Add to Wishlist"
    buttons.append([
        InlineKeyboardButton(wish_label,            callback_data=f"wish_{product_id}"),
        InlineKeyboardButton("📤 Share",            callback_data=f"share_{product_id}"),
    ])
    buttons.append([InlineKeyboardButton(f"⬅️ Back", callback_data=f"cat_{category}")])
    return InlineKeyboardMarkup(buttons)


def featured_products_keyboard(products: list) -> InlineKeyboardMarkup:
    buttons = []
    for p in products:
        price = p["discount_price"] or p["price"]
        label = f"⭐ {p['name'][:28]} — ৳{int(price):,}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"product_{p['product_id']}")])
    buttons.append([InlineKeyboardButton("🛍️ All Categories", callback_data="browse_products")])
    buttons.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


# ═══════════════════════════════════════════════════════════════════
# CART KEYBOARDS
# ═══════════════════════════════════════════════════════════════════

def cart_keyboard(items: list) -> InlineKeyboardMarkup:
    buttons = []
    for item in items:
        name = item["name"][:20]
        buttons.append([
            InlineKeyboardButton(f"➖", callback_data=f"cartqty_{item['product_id']}_dec"),
            InlineKeyboardButton(f"{name} x{item['quantity']}", callback_data="noop"),
            InlineKeyboardButton(f"➕", callback_data=f"cartqty_{item['product_id']}_inc"),
            InlineKeyboardButton(f"🗑️", callback_data=f"cartdel_{item['product_id']}"),
        ])
    buttons.append([
        InlineKeyboardButton("🛒 Checkout",        callback_data="checkout"),
        InlineKeyboardButton("🗑️ Clear Cart",      callback_data="clear_cart"),
    ])
    buttons.append([InlineKeyboardButton("🛍️ Continue Shopping", callback_data="browse_products")])
    buttons.append([InlineKeyboardButton("🏠 Main Menu",         callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def empty_cart_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍️ Browse Products", callback_data="browse_products")],
        [InlineKeyboardButton("🏠 Main Menu",        callback_data="main_menu")],
    ])


# ═══════════════════════════════════════════════════════════════════
# ORDER / CHECKOUT KEYBOARDS
# ═══════════════════════════════════════════════════════════════════

def delivery_area_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏙️ Inside Dhaka (৳60)",   callback_data="area_inside")],
        [InlineKeyboardButton("🗺️ Outside Dhaka (৳120)", callback_data="area_outside")],
        [InlineKeyboardButton("❌ Cancel",               callback_data="main_menu")],
    ])


def payment_method_keyboard(order_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton("💜 bKash",  callback_data=f"pay_{order_id}_bkash")],
        [InlineKeyboardButton("🟠 Nagad",  callback_data=f"pay_{order_id}_nagad")],
    ]
    if COD_ENABLED:
        buttons.append([InlineKeyboardButton("💵 Cash on Delivery", callback_data=f"pay_{order_id}_cod")])
    buttons.append([InlineKeyboardButton("❌ Cancel", callback_data="my_orders")])
    return InlineKeyboardMarkup(buttons)


def order_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Confirm Order", callback_data="confirm_order"),
            InlineKeyboardButton("❌ Cancel",        callback_data="cancel_order"),
        ]
    ])


def order_placed_keyboard(order_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 Pay Now",       callback_data=f"payorder_{order_id}")],
        [InlineKeyboardButton("📋 My Orders",     callback_data="my_orders")],
        [InlineKeyboardButton("🏠 Main Menu",     callback_data="main_menu")],
    ])


def payment_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("❌ Cancel", callback_data="main_menu")
    ]])


# ═══════════════════════════════════════════════════════════════════
# TRACKING / ORDER VIEW KEYBOARDS
# ═══════════════════════════════════════════════════════════════════

def order_list_keyboard(orders: list) -> InlineKeyboardMarkup:
    from utils.formatters import short_status
    buttons = []
    for o in orders:
        st = short_status(o["status"])
        label = f"#{o['order_id']} | {st} | ৳{int(o['total_price']):,}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"vieworder_{o['order_id']}")])
    buttons.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def order_detail_keyboard(order_id: int, status: str) -> InlineKeyboardMarkup:
    buttons = []
    if status == "pending":
        buttons.append([InlineKeyboardButton("💳 Pay Now", callback_data=f"payorder_{order_id}")])
    buttons.append([
        InlineKeyboardButton("📋 All Orders", callback_data="my_orders"),
        InlineKeyboardButton("🏠 Menu",       callback_data="main_menu"),
    ])
    return InlineKeyboardMarkup(buttons)


# ═══════════════════════════════════════════════════════════════════
# ADMIN KEYBOARDS
# ═══════════════════════════════════════════════════════════════════

def admin_dashboard_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 All Orders",    callback_data="admin_orders_all_0"),
         InlineKeyboardButton("🕐 Pending",       callback_data="admin_orders_pending_0")],
        [InlineKeyboardButton("✅ Confirmed",     callback_data="admin_orders_confirmed_0"),
         InlineKeyboardButton("🚚 Shipped",       callback_data="admin_orders_shipped_0")],
        [InlineKeyboardButton("📦 Add Product",   callback_data="admin_add_product"),
         InlineKeyboardButton("📝 Products",      callback_data="admin_list_products_0")],
        [InlineKeyboardButton("🎫 Coupons",       callback_data="admin_coupons"),
         InlineKeyboardButton("🎟️ Add Coupon",   callback_data="admin_add_coupon")],
        [InlineKeyboardButton("📊 Analytics",     callback_data="admin_analytics"),
         InlineKeyboardButton("👥 Customers",     callback_data="admin_customers")],
        [InlineKeyboardButton("🎫 Tickets",       callback_data="admin_tickets"),
         InlineKeyboardButton("📢 Broadcast",     callback_data="admin_broadcast")],
        [InlineKeyboardButton("⚠️ Low Stock",     callback_data="admin_low_stock"),
         InlineKeyboardButton("🔍 Search Order",  callback_data="admin_search")],
    ])


def admin_order_actions_keyboard(order_id: int, current_status: str) -> InlineKeyboardMarkup:
    STATUS_FLOW = {
        "pending":    [("✅ Confirm Payment", "confirmed"), ("❌ Cancel",   "cancelled")],
        "confirmed":  [("⚙️ Processing",     "processing"), ("❌ Cancel",  "cancelled")],
        "processing": [("📦 Pack",           "packed"),    ("❌ Cancel",   "cancelled")],
        "packed":     [("🚚 Ship",           "shipped")],
        "shipped":    [("✅ Delivered",      "delivered")],
        "delivered":  [],
        "cancelled":  [],
    }
    buttons = []
    for label, status in STATUS_FLOW.get(current_status, []):
        buttons.append([InlineKeyboardButton(label, callback_data=f"admupd_{order_id}_{status}")])
    buttons.append([InlineKeyboardButton("⬅️ Orders", callback_data="admin_orders_all_0")])
    return InlineKeyboardMarkup(buttons)


def admin_product_keyboard(product_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Edit Name",        callback_data=f"admprod_name_{product_id}"),
         InlineKeyboardButton("💰 Edit Price",       callback_data=f"admprod_price_{product_id}")],
        [InlineKeyboardButton("📦 Update Stock",     callback_data=f"admprod_stock_{product_id}"),
         InlineKeyboardButton("🖼️ Set Image",        callback_data=f"admprod_image_{product_id}")],
        [InlineKeyboardButton("🔖 Discount Price",   callback_data=f"admprod_discount_{product_id}"),
         InlineKeyboardButton("⭐ Toggle Featured",  callback_data=f"admprod_featured_{product_id}")],
        [InlineKeyboardButton("🗑️ Delete Product",   callback_data=f"admprod_delete_{product_id}")],
        [InlineKeyboardButton("⬅️ Products List",    callback_data="admin_list_products_0")],
    ])


def admin_products_list_keyboard(products: list, page: int, has_more: bool) -> InlineKeyboardMarkup:
    buttons = []
    for p in products:
        status = "✅" if p["is_active"] else "❌"
        label = f"{status} {p['name'][:25]} | ৳{int(p['price']):,} | Stock:{p['stock']}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"admview_prod_{p['product_id']}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"admin_list_products_{page-1}"))
    if has_more:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"admin_list_products_{page+1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("⬅️ Admin Panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(buttons)


def admin_ticket_keyboard(ticket_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💬 Reply",    callback_data=f"admticket_reply_{ticket_id}"),
         InlineKeyboardButton("✅ Close",    callback_data=f"admticket_close_{ticket_id}")],
        [InlineKeyboardButton("⬅️ Tickets", callback_data="admin_tickets")],
    ])


# ═══════════════════════════════════════════════════════════════════
# PROFILE / WISHLIST / SUPPORT
# ═══════════════════════════════════════════════════════════════════

def profile_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 My Orders",    callback_data="my_orders"),
         InlineKeyboardButton("❤️ Wishlist",     callback_data="my_wishlist")],
        [InlineKeyboardButton("🕐 Recently Seen", callback_data="recently_viewed"),
         InlineKeyboardButton("🎫 My Coupons",   callback_data="use_coupon")],
        [InlineKeyboardButton("🏠 Main Menu",    callback_data="main_menu")],
    ])


def wishlist_keyboard(products: list) -> InlineKeyboardMarkup:
    buttons = []
    for p in products:
        price = p["discount_price"] or p["price"]
        buttons.append([
            InlineKeyboardButton(f"🛍️ {p['name'][:22]}", callback_data=f"product_{p['product_id']}"),
            InlineKeyboardButton("💔 Remove",             callback_data=f"wish_{p['product_id']}"),
        ])
    buttons.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def support_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎫 New Ticket",     callback_data="new_ticket")],
        [InlineKeyboardButton("📋 My Tickets",     callback_data="my_tickets")],
        [InlineKeyboardButton("🏠 Main Menu",      callback_data="main_menu")],
    ])
