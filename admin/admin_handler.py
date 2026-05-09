"""
admin/admin_handler.py
=======================
Complete admin dashboard: orders, products, analytics, broadcast,
coupons, customers, support tickets, low stock alerts.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database.queries import (
    get_all_orders, get_order, get_order_items, update_order_status,
    count_orders_by_status, get_all_users, get_user_count,
    get_revenue_stats, get_top_products, get_daily_stats,
    get_all_products_admin, get_product, update_product_field,
    add_product, delete_product, get_low_stock_products,
    get_all_coupons, create_coupon,
    get_open_tickets, reply_ticket,
    get_top_customers, log_event,
)
from keyboards.builder import (
    admin_dashboard_keyboard, admin_order_actions_keyboard,
    admin_product_keyboard, admin_products_list_keyboard,
    admin_ticket_keyboard, back_to_menu,
)
from utils.helpers import admin_only, safe_edit, safe_answer, notify_user
from utils.formatters import (
    format_order_card, format_analytics, format_price,
    format_order_notification, short_status,
)

logger = logging.getLogger(__name__)

# ─── Conversation States ──────────────────────────────────────────────────────
BROADCAST_MSG   = 30
ADD_PROD_NAME   = 31
ADD_PROD_CAT    = 32
ADD_PROD_DESC   = 33
ADD_PROD_PRICE  = 34
ADD_PROD_DISC   = 35
ADD_PROD_STOCK  = 36
ADD_PROD_IMAGE  = 37
EDIT_PROD_VAL   = 38
ADD_COUPON_CODE = 39
ADD_COUPON_DISC = 40
ADD_COUPON_MIN  = 41
TICKET_REPLY    = 42

PAGE_SIZE = 5


# ═══════════════════════════════════════════════════════════════════
# DASHBOARD
# ═══════════════════════════════════════════════════════════════════

@admin_only
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main admin dashboard."""
    counts = count_orders_by_status()
    total  = sum(counts.values())
    stats  = get_revenue_stats()
    users  = get_user_count()

    text = (
        f"🛠️ *Admin Dashboard — PickDeal BD*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 *Total Users:* {users:,}\n"
        f"📋 *Total Orders:* {total:,}\n"
        f"💰 *Total Revenue:* {format_price(stats.get('total_revenue', 0))}\n"
        f"📅 *Today Revenue:* {format_price(stats.get('today_revenue', 0))}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 Pending:    {counts.get('pending', 0)}\n"
        f"✅ Confirmed:  {counts.get('confirmed', 0)}\n"
        f"⚙️ Processing: {counts.get('processing', 0)}\n"
        f"📦 Packed:     {counts.get('packed', 0)}\n"
        f"🚚 Shipped:    {counts.get('shipped', 0)}\n"
        f"✅ Delivered:  {counts.get('delivered', 0)}\n"
        f"❌ Cancelled:  {counts.get('cancelled', 0)}\n"
    )

    if update.callback_query:
        await safe_answer(update.callback_query)
        await safe_edit(update.callback_query, text, reply_markup=admin_dashboard_keyboard())
    else:
        await update.message.reply_text(text, parse_mode="Markdown",
                                        reply_markup=admin_dashboard_keyboard())


# ═══════════════════════════════════════════════════════════════════
# ORDER MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

@admin_only
async def admin_view_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Paginated order list filtered by status."""
    query = update.callback_query
    await safe_answer(query)

    # Pattern: admin_orders_<status>_<page>
    parts  = query.data.split("_")
    status = parts[2]
    page   = int(parts[3])
    offset = page * PAGE_SIZE

    orders = get_all_orders(status_filter=status, limit=PAGE_SIZE, offset=offset)

    if not orders:
        await safe_edit(
            query,
            f"📭 *{status.title()}* — কোনো অর্ডার নেই।",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Dashboard", callback_data="admin_panel")
            ]])
        )
        return

    buttons = []
    for o in orders:
        st = short_status(o["status"])
        label = f"#{o['order_id']} | {o['first_name'][:10]} | {format_price(o['total_price'])} | {st}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"admview_{o['order_id']}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"admin_orders_{status}_{page-1}"))
    if len(orders) == PAGE_SIZE:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"admin_orders_{status}_{page+1}"))
    if nav:
        buttons.append(nav)
    buttons.append([InlineKeyboardButton("⬅️ Dashboard", callback_data="admin_panel")])

    await safe_edit(
        query,
        f"📋 *Orders — {status.title()}* (Page {page+1})",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@admin_only
async def admin_view_order_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View order detail and show action buttons."""
    query = update.callback_query
    await safe_answer(query)

    order_id = int(query.data.split("_")[1])
    order = get_order(order_id)
    if not order:
        await query.answer(f"❌ Order #{order_id} not found!", show_alert=True)
        return

    items = get_order_items(order_id)
    items_text = "\n".join(
        f"  • {i['product_name']} × {i['quantity']} = {format_price(i['total_price'])}"
        for i in items
    )

    text = (
        f"🛠️ *Order Detail*\n"
        f"{format_order_card(order)}\n\n"
        f"📦 *Items:*\n{items_text}\n"
        f"👤 *Customer ID:* {order['user_id']}"
    )

    await safe_edit(
        query,
        text,
        reply_markup=admin_order_actions_keyboard(order_id, order["status"])
    )


@admin_only
async def admin_update_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update order status and notify customer."""
    query = update.callback_query
    await safe_answer(query)

    # Pattern: admupd_<order_id>_<new_status>
    parts      = query.data.split("_")
    order_id   = int(parts[1])
    new_status = parts[2]

    order = get_order(order_id)
    if not order:
        await query.answer("❌ Order not found!", show_alert=True)
        return

    update_order_status(order_id, new_status)
    log_event("order_status_changed", order_id=order_id)

    # Notify customer
    customer_msg = format_order_notification(order_id, new_status, order)
    sent = await notify_user(
        context, order["user_id"], customer_msg, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📋 My Orders", callback_data="my_orders")
        ]])
    )

    status_label = new_status.replace("_", " ").title()
    await query.answer(f"✅ Status → {status_label} | Customer notified: {'✓' if sent else '✗'}")

    # Reload detail view
    order = get_order(order_id)
    items = get_order_items(order_id)
    items_text = "\n".join(
        f"  • {i['product_name']} × {i['quantity']} = {format_price(i['total_price'])}"
        for i in items
    )
    text = (
        f"🛠️ *Order Detail*\n"
        f"{format_order_card(order)}\n\n"
        f"📦 *Items:*\n{items_text}"
    )
    await safe_edit(
        query,
        text,
        reply_markup=admin_order_actions_keyboard(order_id, order["status"])
    )


@admin_only
async def admin_search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt admin for order ID search."""
    query = update.callback_query
    await safe_answer(query)
    context.user_data["admin_search_active"] = True
    await safe_edit(
        query,
        "🔍 *Search Order by ID*\n\nOrder ID লিখুন:\n_(Example: 42)_",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Cancel", callback_data="admin_panel")
        ]])
    )


@admin_only
async def admin_search_order_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle order ID input for admin search."""
    if not context.user_data.get("admin_search_active"):
        return

    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("⚠️ শুধু নম্বর দিন।")
        return

    context.user_data.pop("admin_search_active", None)
    order_id = int(text)
    order = get_order(order_id)

    if not order:
        await update.message.reply_text(
            f"❌ Order #{order_id} পাওয়া যায়নি।",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Dashboard", callback_data="admin_panel")
            ]])
        )
        return

    items = get_order_items(order_id)
    items_text = "\n".join(
        f"  • {i['product_name']} × {i['quantity']} = {format_price(i['total_price'])}"
        for i in items
    )
    text_out = (
        f"🛠️ *Order Detail*\n"
        f"{format_order_card(order)}\n\n"
        f"📦 *Items:*\n{items_text}"
    )
    await update.message.reply_text(
        text_out,
        parse_mode="Markdown",
        reply_markup=admin_order_actions_keyboard(order_id, order["status"])
    )


# ═══════════════════════════════════════════════════════════════════
# PRODUCT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════

@admin_only
async def admin_list_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Paginated product list for admin."""
    query = update.callback_query
    await safe_answer(query)
    page   = int(query.data.split("_")[-1])
    offset = page * PAGE_SIZE

    products = get_all_products_admin(limit=PAGE_SIZE, offset=offset)
    has_more = len(products) == PAGE_SIZE

    await safe_edit(
        query,
        f"📦 *Product Management* (Page {page+1})",
        reply_markup=admin_products_list_keyboard(products, page, has_more)
    )


@admin_only
async def admin_view_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View single product admin panel."""
    query = update.callback_query
    await safe_answer(query)
    product_id = int(query.data.split("_")[-1])
    p = get_product(product_id)
    if not p:
        await query.answer("❌ পণ্য পাওয়া যায়নি!", show_alert=True)
        return

    status = "✅ Active" if p["is_active"] else "❌ Inactive"
    featured = "⭐ Yes" if p["is_featured"] else "No"
    text = (
        f"📦 *Product Admin*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: {p['product_id']}\n"
        f"📛 Name: {p['name']}\n"
        f"🏷️ Category: {p['category']}\n"
        f"💰 Price: {format_price(p['price'])}\n"
        f"🔖 Discount: {format_price(p['discount_price'] or p['price'])}\n"
        f"📦 Stock: {p['stock']}\n"
        f"⭐ Featured: {featured}\n"
        f"🚦 Status: {status}\n"
        f"📅 Created: {str(p['created_at'])[:16]}"
    )
    await safe_edit(query, text, reply_markup=admin_product_keyboard(product_id))


# ── Add Product Flow ──────────────────────────────────────────────

@admin_only
async def admin_add_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    context.user_data["new_product"] = {}
    await safe_edit(
        query,
        "📦 *Add New Product*\n\n*Step 1:* পণ্যের নাম লিখুন:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")
        ]])
    )
    return ADD_PROD_NAME


async def add_prod_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_product"]["name"] = update.message.text.strip()
    await update.message.reply_text(
        "✅ নাম সংরক্ষিত!\n\n*Step 2:* Category লিখুন:\n"
        "_(Fashion / Gadgets / Umbrellas / Accessories / Home & Living)_",
        parse_mode="Markdown"
    )
    return ADD_PROD_CAT


async def add_prod_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_product"]["category"] = update.message.text.strip()
    await update.message.reply_text("✅\n\n*Step 3:* পণ্যের বিবরণ লিখুন:", parse_mode="Markdown")
    return ADD_PROD_DESC


async def add_prod_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_product"]["description"] = update.message.text.strip()
    await update.message.reply_text("✅\n\n*Step 4:* মূল্য লিখুন (শুধু সংখ্যা, যেমন: 1299):", parse_mode="Markdown")
    return ADD_PROD_PRICE


async def add_prod_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["new_product"]["price"] = float(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("⚠️ সঠিক মূল্য দিন (যেমন: 1299):")
        return ADD_PROD_PRICE
    await update.message.reply_text(
        "✅\n\n*Step 5:* ডিসকাউন্ট মূল্য লিখুন\n_(না থাকলে 0 দিন)_:", parse_mode="Markdown"
    )
    return ADD_PROD_DISC


async def add_prod_disc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["new_product"]["discount_price"] = float(update.message.text.strip())
    except ValueError:
        context.user_data["new_product"]["discount_price"] = 0
    await update.message.reply_text("✅\n\n*Step 6:* স্টক সংখ্যা লিখুন:", parse_mode="Markdown")
    return ADD_PROD_STOCK


async def add_prod_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["new_product"]["stock"] = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("⚠️ সঠিক সংখ্যা দিন:")
        return ADD_PROD_STOCK
    await update.message.reply_text(
        "✅\n\n*Step 7:* পণ্যের ছবি পাঠান\n_(না থাকলে 'skip' লিখুন)_:", parse_mode="Markdown"
    )
    return ADD_PROD_IMAGE


async def add_prod_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    np = context.user_data["new_product"]
    image_url = None

    if update.message.photo:
        image_url = update.message.photo[-1].file_id
    elif update.message.text and update.message.text.lower() != "skip":
        image_url = update.message.text.strip()

    product_id = add_product(
        name=np["name"],
        category=np["category"],
        description=np["description"],
        price=np["price"],
        discount_price=np.get("discount_price") or np["price"],
        stock=np["stock"],
        image_url=image_url,
    )

    await update.message.reply_text(
        f"✅ *পণ্য সফলভাবে যোগ হয়েছে!*\n\n"
        f"🆔 Product ID: {product_id}\n"
        f"📛 Name: {np['name']}\n"
        f"💰 Price: {format_price(np['price'])}\n"
        f"📦 Stock: {np['stock']}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Dashboard", callback_data="admin_panel")
        ]])
    )
    context.user_data.pop("new_product", None)
    return ConversationHandler.END


# ── Edit Product ──────────────────────────────────────────────────

@admin_only
async def admin_edit_product_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt for new field value."""
    query = update.callback_query
    await safe_answer(query)

    # admprod_<field>_<product_id>
    parts      = query.data.split("_")
    field      = parts[1]
    product_id = int(parts[2])

    if field == "featured":
        p = get_product(product_id)
        new_val = 0 if p["is_featured"] else 1
        update_product_field(product_id, "is_featured", new_val)
        label = "⭐ Featured" if new_val else "Not Featured"
        await query.answer(f"✅ {label}", show_alert=False)
        await admin_view_product(update, context)
        return ConversationHandler.END

    if field == "delete":
        delete_product(product_id)
        await safe_edit(
            query,
            f"🗑️ Product #{product_id} deleted (hidden).",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Products", callback_data="admin_list_products_0")
            ]])
        )
        return ConversationHandler.END

    field_labels = {
        "name": "নতুন নাম", "price": "নতুন মূল্য (৳)",
        "discount": "নতুন ডিসকাউন্ট মূল্য (৳)",
        "stock": "নতুন স্টক সংখ্যা", "image": "নতুন Image (ছবি পাঠান বা URL)",
    }
    context.user_data["edit_product"] = {"field": field, "product_id": product_id}
    await safe_edit(
        query,
        f"✏️ *Edit Product #{product_id}*\n\n{field_labels.get(field, field)} লিখুন:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data=f"admview_prod_{product_id}")
        ]])
    )
    return EDIT_PROD_VAL


async def admin_save_product_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save edited product field."""
    ep = context.user_data.get("edit_product", {})
    field      = ep.get("field")
    product_id = ep.get("product_id")

    field_map = {
        "name": "name", "price": "price",
        "discount": "discount_price", "stock": "stock", "image": "image_url",
    }
    db_field = field_map.get(field, field)

    value = None
    if update.message.photo and field == "image":
        value = update.message.photo[-1].file_id
    else:
        value = update.message.text.strip()
        if field in ("price", "discount"):
            try:
                value = float(value)
            except ValueError:
                await update.message.reply_text("⚠️ সঠিক মূল্য দিন:")
                return EDIT_PROD_VAL
        elif field == "stock":
            try:
                value = int(value)
            except ValueError:
                await update.message.reply_text("⚠️ সঠিক সংখ্যা দিন:")
                return EDIT_PROD_VAL

    update_product_field(product_id, db_field, value)
    context.user_data.pop("edit_product", None)

    await update.message.reply_text(
        f"✅ Product #{product_id} আপডেট হয়েছে!",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📦 View Product", callback_data=f"admview_prod_{product_id}"),
            InlineKeyboardButton("⬅️ Dashboard",  callback_data="admin_panel"),
        ]])
    )
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════════════
# ANALYTICS
# ═══════════════════════════════════════════════════════════════════

@admin_only
async def admin_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    stats    = get_revenue_stats()
    counts   = count_orders_by_status()
    users    = get_user_count()
    top_prod = get_top_products(5)
    daily    = get_daily_stats(7)
    text     = format_analytics(stats, counts, users, top_prod, daily)
    await safe_edit(
        query, text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Dashboard", callback_data="admin_panel")
        ]])
    )


# ═══════════════════════════════════════════════════════════════════
# CUSTOMERS
# ═══════════════════════════════════════════════════════════════════

@admin_only
async def admin_customers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    top = get_top_customers(10)
    total = get_user_count()

    lines = [f"👥 *Customer Overview*\n", f"Total Users: *{total:,}*\n", "━━━━━━━━━━━━━━━━━━━━"]
    lines.append("🏆 *Top Customers:*")
    for i, c in enumerate(top, 1):
        uname = f"@{c['username']}" if c["username"] else c["first_name"]
        lines.append(
            f"{i}. {uname} | {c['total_orders']} orders | {format_price(c['total_spent'] or 0)}"
        )

    await safe_edit(
        query, "\n".join(lines),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Dashboard", callback_data="admin_panel")
        ]])
    )


# ═══════════════════════════════════════════════════════════════════
# BROADCAST
# ═══════════════════════════════════════════════════════════════════

@admin_only
async def admin_broadcast_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    await safe_edit(
        query,
        "📢 *Broadcast Message*\n\n"
        "সব Users কে পাঠানোর জন্য বার্তা লিখুন:\n"
        "_(Markdown formatting সমর্থিত)_",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")
        ]])
    )
    return BROADCAST_MSG


@admin_only
async def admin_send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send broadcast to all non-banned users."""
    message_text = update.message.text
    user_ids = get_all_users()
    sent = failed = 0

    status_msg = await update.message.reply_text(
        f"📢 {len(user_ids)} জন User-কে পাঠানো হচ্ছে..."
    )

    for uid in user_ids:
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=f"📢 *PickDeal BD — বিশেষ বার্তা*\n\n{message_text}",
                parse_mode="Markdown",
            )
            sent += 1
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"✅ *Broadcast সম্পন্ন!*\n\n"
        f"✔️ পাঠানো হয়েছে: {sent}\n"
        f"❌ ব্যর্থ: {failed}",
        parse_mode="Markdown"
    )
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════════════
# COUPONS
# ═══════════════════════════════════════════════════════════════════

@admin_only
async def admin_coupons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    coupons = get_all_coupons()

    if not coupons:
        await safe_edit(
            query, "🎫 কোনো Coupon নেই।",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ Add Coupon", callback_data="admin_add_coupon")],
                [InlineKeyboardButton("⬅️ Dashboard",  callback_data="admin_panel")],
            ])
        )
        return

    lines = ["🎫 *All Coupons*\n"]
    for c in coupons:
        disc = f"{c['discount_pct']}%" if c["discount_pct"] > 0 else f"৳{int(c['discount_flat'])}"
        st   = "✅" if c["is_active"] else "❌"
        lines.append(
            f"{st} `{c['code']}` — {disc} | Min: ৳{int(c['min_order'])} "
            f"| Used: {c['used_count']}/{c['max_uses']}"
        )

    await safe_edit(
        query, "\n".join(lines),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Add Coupon", callback_data="admin_add_coupon")],
            [InlineKeyboardButton("⬅️ Dashboard",  callback_data="admin_panel")],
        ])
    )


@admin_only
async def admin_add_coupon_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    context.user_data["new_coupon"] = {}
    await safe_edit(
        query, "🎫 *Add Coupon*\n\n*Step 1:* Coupon Code লিখুন:\n_(যেমন: SUMMER20)_",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="admin_coupons")
        ]])
    )
    return ADD_COUPON_CODE


async def add_coupon_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_coupon"]["code"] = update.message.text.strip().upper()
    await update.message.reply_text(
        "✅\n\n*Step 2:* ডিসকাউন্ট % লিখুন\n_(flat টাকা হলে 0 দিন, যেমন: 10)_:",
        parse_mode="Markdown"
    )
    return ADD_COUPON_DISC


async def add_coupon_disc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["new_coupon"]["discount_pct"] = float(update.message.text.strip())
    except ValueError:
        context.user_data["new_coupon"]["discount_pct"] = 0
    await update.message.reply_text(
        "✅\n\n*Step 3:* ন্যূনতম অর্ডার পরিমাণ লিখুন (৳):\n_(না থাকলে 0 দিন)_:",
        parse_mode="Markdown"
    )
    return ADD_COUPON_MIN


async def add_coupon_min(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nc = context.user_data["new_coupon"]
    try:
        nc["min_order"] = float(update.message.text.strip())
    except ValueError:
        nc["min_order"] = 0

    create_coupon(
        code=nc["code"],
        discount_pct=nc.get("discount_pct", 0),
        min_order=nc.get("min_order", 0),
        max_uses=1000,
    )

    await update.message.reply_text(
        f"✅ *Coupon '{nc['code']}' সফলভাবে তৈরি হয়েছে!*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Coupons", callback_data="admin_coupons")
        ]])
    )
    context.user_data.pop("new_coupon", None)
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════════════
# LOW STOCK
# ═══════════════════════════════════════════════════════════════════

@admin_only
async def admin_low_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    products = get_low_stock_products(threshold=10)

    if not products:
        await safe_edit(
            query, "✅ *কোনো Low Stock পণ্য নেই!*\n\nসব পণ্যের স্টক ঠিক আছে।",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Dashboard", callback_data="admin_panel")
            ]])
        )
        return

    lines = ["⚠️ *Low Stock Alert*\n"]
    for p in products:
        icon = "❌" if p["stock"] == 0 else "⚠️"
        lines.append(f"{icon} *{p['name'][:30]}* — {p['stock']} left")

    await safe_edit(
        query, "\n".join(lines),
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📦 Products", callback_data="admin_list_products_0"),
            InlineKeyboardButton("⬅️ Dashboard", callback_data="admin_panel"),
        ]])
    )


# ═══════════════════════════════════════════════════════════════════
# SUPPORT TICKETS (ADMIN SIDE)
# ═══════════════════════════════════════════════════════════════════

@admin_only
async def admin_view_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    tickets = get_open_tickets(limit=10)

    if not tickets:
        await safe_edit(
            query, "🎫 *Open Support Tickets*\n\nকোনো Open টিকেট নেই! ✅",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Dashboard", callback_data="admin_panel")
            ]])
        )
        return

    buttons = []
    for t in tickets:
        name = t["first_name"] or "User"
        label = f"#{t['ticket_id']} | {name} | {t['message'][:30]}..."
        buttons.append([InlineKeyboardButton(label, callback_data=f"admticket_view_{t['ticket_id']}")])
    buttons.append([InlineKeyboardButton("⬅️ Dashboard", callback_data="admin_panel")])

    await safe_edit(
        query, f"🎫 *Open Tickets* ({len(tickets)})",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


@admin_only
async def admin_view_ticket_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    ticket_id = int(query.data.split("_")[-1])

    from database.db_setup import get_connection
    with get_connection() as conn:
        t = conn.execute("""
            SELECT t.*, u.first_name, u.username
            FROM support_tickets t JOIN users u ON t.user_id = u.user_id
            WHERE t.ticket_id = ?
        """, (ticket_id,)).fetchone()

    if not t:
        await query.answer("❌ Ticket not found!", show_alert=True)
        return

    uname = f"@{t['username']}" if t["username"] else t["first_name"]
    text = (
        f"🎫 *Ticket #{ticket_id}*\n"
        f"👤 {uname} | ID: {t['user_id']}\n"
        f"📅 {str(t['created_at'])[:16]}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💬 {t['message']}\n"
    )
    if t.get("reply"):
        text += f"━━━━━━━━━━━━━━━━━━━━\n📩 *Reply:* {t['reply']}"

    await safe_edit(query, text, reply_markup=admin_ticket_keyboard(ticket_id))


@admin_only
async def admin_reply_ticket_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    ticket_id = int(query.data.split("_")[-1])
    context.user_data["replying_ticket"] = ticket_id
    await safe_edit(
        query, f"📩 *Ticket #{ticket_id} Reply*\n\nআপনার উত্তর লিখুন:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="admin_tickets")
        ]])
    )
    return TICKET_REPLY


@admin_only
async def admin_send_ticket_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticket_id = context.user_data.get("replying_ticket")
    reply_text = update.message.text.strip()
    admin_id = update.effective_user.id

    # Get ticket user
    from database.db_setup import get_connection
    with get_connection() as conn:
        t = conn.execute("SELECT * FROM support_tickets WHERE ticket_id=?", (ticket_id,)).fetchone()

    if not t:
        await update.message.reply_text("❌ Ticket not found.")
        return ConversationHandler.END

    reply_ticket(ticket_id, reply_text, admin_id)

    # Notify customer
    await notify_user(
        context, t["user_id"],
        f"📩 *Support Reply — Ticket #{ticket_id}*\n\n"
        f"PickDeal BD Support Team এর উত্তর:\n\n{reply_text}\n\n"
        f"আরো সাহায্যের জন্য নতুন টিকেট খুলুন।",
        parse_mode="Markdown"
    )

    await update.message.reply_text(
        f"✅ Ticket #{ticket_id} reply পাঠানো হয়েছে!",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Tickets", callback_data="admin_tickets")
        ]])
    )
    context.user_data.pop("replying_ticket", None)
    return ConversationHandler.END


@admin_only
async def admin_close_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    ticket_id = int(query.data.split("_")[-1])
    from database.db_setup import get_connection
    with get_connection() as conn:
        conn.execute(
            "UPDATE support_tickets SET status='closed', updated_at=datetime('now') WHERE ticket_id=?",
            (ticket_id,)
        )
    await query.answer(f"✅ Ticket #{ticket_id} closed.", show_alert=False)
    await admin_view_tickets(update, context)
