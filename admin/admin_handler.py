"""
admin/admin_handler.py — PickDeal BD v3
Full admin dashboard. All bugs fixed. New features added.
FIX: Open Tickets callback now works.
NEW: Category add/edit/delete/toggle/feature.
NEW: Delivery method CRUD.
NEW: Payment method toggle/edit.
NEW: Coupon edit/delete/toggle.
NEW: Single user message.
NEW: Ticket reopen.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database.queries import (
    get_all_orders, get_order, get_order_items, update_order_status,
    count_orders_by_status, get_all_user_ids, get_user_count, get_user,
    get_revenue_stats, get_top_products, get_daily_stats,
    get_all_products_admin, get_product, update_product_field,
    add_product, soft_delete_product, get_low_stock_products, add_product_image,
    get_categories, get_category, add_category, update_category, delete_category,
    get_delivery_methods, get_delivery_method, add_delivery_method,
    update_delivery_method, delete_delivery_method,
    get_payment_methods, get_payment_method, update_payment_method, add_payment_method,
    get_all_coupons, get_coupon, create_coupon, update_coupon, delete_coupon,
    get_open_tickets, get_ticket, reply_ticket, set_ticket_status,
    get_top_customers, log_event,
)
from keyboards.builder import (
    admin_dashboard_keyboard, admin_order_actions_keyboard,
    admin_product_keyboard, admin_products_list_keyboard,
    admin_categories_keyboard, admin_category_detail_keyboard,
    admin_delivery_keyboard, admin_delivery_detail_keyboard,
    admin_payment_methods_keyboard, admin_payment_detail_keyboard,
    admin_coupons_keyboard, admin_coupon_detail_keyboard,
    admin_ticket_keyboard,
)
from utils.helpers import admin_only, safe_edit, safe_answer, notify_user
from utils.formatters import (
    format_order_card, format_analytics, format_price,
    format_order_notification, short_status,
)

logger = logging.getLogger(__name__)

# ── States ────────────────────────────────────────────────────────
(
    BROADCAST_MSG, MSG_USER_ID, MSG_USER_TEXT,
    ADD_PROD_NAME, ADD_PROD_CAT, ADD_PROD_DESC,
    ADD_PROD_PRICE, ADD_PROD_DISC, ADD_PROD_STOCK, ADD_PROD_IMAGE,
    EDIT_PROD_VAL,
    ADD_CAT_NAME, ADD_CAT_EMOJI, EDIT_CAT_VAL,
    ADD_DLV_NAME, ADD_DLV_DESC, ADD_DLV_CHARGE, EDIT_DLV_VAL,
    ADD_PM_NAME, ADD_PM_NUM, ADD_PM_DESC, EDIT_PM_VAL,
    ADD_CPN_CODE, ADD_CPN_TYPE, ADD_CPN_VAL, ADD_CPN_MIN, ADD_CPN_EXP, EDIT_CPN_VAL,
    TICKET_REPLY_STATE, ORDER_NOTE_STATE,
) = range(60, 90)

PAGE = 5


# ════════════════════════════════════════════════
# DASHBOARD
# ════════════════════════════════════════════════

@admin_only
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    counts = count_orders_by_status()
    stats  = get_revenue_stats()
    users  = get_user_count()
    text = (
        f"🛠️ *Admin Dashboard — PickDeal BD*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 *ইউজার:* {users:,}\n"
        f"📋 *মোট অর্ডার:* {sum(counts.values()):,}\n"
        f"💰 *মোট রেভিনিউ:* {format_price(stats.get('total_revenue',0))}\n"
        f"📅 *আজকের রেভিনিউ:* {format_price(stats.get('today_revenue',0))}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 পেন্ডিং: {counts.get('pending',0)}  "
        f"✅ নিশ্চিত: {counts.get('confirmed',0)}  "
        f"🚚 শিপড: {counts.get('shipped',0)}  "
        f"🎉 ডেলিভারি: {counts.get('delivered',0)}"
    )
    if update.callback_query:
        await safe_answer(update.callback_query)
        await safe_edit(update.callback_query, text, reply_markup=admin_dashboard_keyboard())
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=admin_dashboard_keyboard())


# ════════════════════════════════════════════════
# ORDER MANAGEMENT
# ════════════════════════════════════════════════

@admin_only
async def admin_view_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await safe_answer(query)
    parts  = query.data.split("_")   # adm_orders_<status>_<page>
    status = parts[2]
    page   = int(parts[3])
    orders = get_all_orders(status_filter=status, limit=PAGE, offset=page * PAGE)
    if not orders:
        await safe_edit(query, f"📭 *{status.title()}* — কোনো অর্ডার নেই।",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Dashboard", callback_data="adm_panel")]]))
        return
    buttons = []
    for o in orders:
        st    = short_status(o["status"])
        label = f"#{o['order_id']} | {o['first_name'][:8]} | {format_price(o['total_price'])} | {st}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"adm_order_{o['order_id']}")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"adm_orders_{status}_{page-1}"))
    if len(orders) == PAGE:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"adm_orders_{status}_{page+1}"))
    if nav: buttons.append(nav)
    buttons.append([InlineKeyboardButton("⬅️ Dashboard", callback_data="adm_panel")])
    await safe_edit(query, f"📋 *অর্ডার — {status.title()}* (পাতা {page+1})",
                    reply_markup=InlineKeyboardMarkup(buttons))


@admin_only
async def admin_view_order_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await safe_answer(query)
    order_id = int(query.data.split("_")[-1])
    order    = get_order(order_id)
    if not order:
        await query.answer(f"❌ Order #{order_id} পাওয়া যায়নি!", show_alert=True)
        return
    items      = get_order_items(order_id)
    items_text = "\n".join(f"  • {i['product_name']} × {i['quantity']} = {format_price(i['total_price'])}" for i in items)
    text = f"🛠️ *Order Detail*\n{format_order_card(order)}\n\n📦 *পণ্য:*\n{items_text}\n👤 User ID: `{order['user_id']}`"
    await safe_edit(query, text, reply_markup=admin_order_actions_keyboard(order_id, order["status"]))


@admin_only
async def admin_update_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query      = update.callback_query
    await safe_answer(query)
    parts      = query.data.split("_")
    order_id   = int(parts[1])
    new_status = "_".join(parts[2:])
    order      = get_order(order_id)
    if not order:
        await query.answer("❌ Order not found!", show_alert=True)
        return
    update_order_status(order_id, new_status)
    log_event("order_status_changed", order_id=order_id)
    msg  = format_order_notification(order_id, new_status)
    sent = await notify_user(context, order["user_id"], msg, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 আমার অর্ডার", callback_data="my_orders")]]))
    await query.answer(f"✅ → {new_status} | নোটিফিকেশন: {'✓' if sent else '✗'}")
    order = get_order(order_id)
    items      = get_order_items(order_id)
    items_text = "\n".join(f"  • {i['product_name']} × {i['quantity']}" for i in items)
    await safe_edit(query, f"🛠️ *Order Detail*\n{format_order_card(order)}\n\n📦 *পণ্য:*\n{items_text}",
                    reply_markup=admin_order_actions_keyboard(order_id, order["status"]))


@admin_only
async def admin_order_note_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await safe_answer(query)
    order_id = int(query.data.split("_")[-1])
    context.user_data["note_order_id"] = order_id
    await safe_edit(query, f"📝 Order #{order_id} — নোট লিখুন:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data=f"adm_order_{order_id}")]]))
    return ORDER_NOTE_STATE


@admin_only
async def admin_order_note_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    order_id = context.user_data.pop("note_order_id", None)
    if not order_id:
        return ConversationHandler.END
    update_order_status(order_id, get_order(order_id)["status"], admin_note=update.message.text.strip())
    await update.message.reply_text(f"✅ Order #{order_id} নোট সংরক্ষিত!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Order", callback_data=f"adm_order_{order_id}")]]))
    return ConversationHandler.END


# ════════════════════════════════════════════════
# PRODUCT MANAGEMENT
# ════════════════════════════════════════════════

@admin_only
async def admin_list_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await safe_answer(query)
    page   = int(query.data.split("_")[-1])
    prods  = get_all_products_admin(limit=PAGE, offset=page * PAGE)
    await safe_edit(query, f"📦 *পণ্য ম্যানেজমেন্ট* (পাতা {page+1})",
                    reply_markup=admin_products_list_keyboard(prods, page, len(prods) == PAGE))


@admin_only
async def admin_view_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query      = update.callback_query
    await safe_answer(query)
    product_id = int(query.data.split("_")[-1])
    p = get_product(product_id)
    if not p:
        await query.answer("❌ পণ্য পাওয়া যায়নি!", show_alert=True)
        return
    text = (
        f"📦 *Product Admin*\n━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 ID: {p['product_id']}\n"
        f"📛 নাম: {p['name']}\n"
        f"🏷️ ক্যাটাগরি: {p['category']}\n"
        f"💰 মূল্য: {format_price(p['price'])}\n"
        f"🔖 ডিসকাউন্ট: {format_price(p['discount_price'] or p['price'])}\n"
        f"📦 স্টক: {p['stock']}\n"
        f"⭐ Featured: {'হ্যাঁ' if p['is_featured'] else 'না'}\n"
        f"🚦 Status: {'✅ Active' if p['is_active'] else '❌ Inactive'}"
    )
    await safe_edit(query, text, reply_markup=admin_product_keyboard(product_id))


@admin_only
async def admin_add_product_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    context.user_data["np"] = {}
    await safe_edit(query, "📦 *পণ্য যোগ*\n\n*ধাপ ১:* পণ্যের নাম লিখুন:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data="adm_panel")]]))
    return ADD_PROD_NAME


async def _ap_name(u, c):
    c.user_data["np"]["name"] = u.message.text.strip()
    await u.message.reply_text("✅\n\n*ধাপ ২:* ক্যাটাগরি লিখুন:\n_(Fashion/Gadgets/Umbrellas...)_", parse_mode="Markdown")
    return ADD_PROD_CAT

async def _ap_cat(u, c):
    c.user_data["np"]["category"] = u.message.text.strip()
    await u.message.reply_text("✅\n\n*ধাপ ৩:* পণ্যের বিবরণ লিখুন:", parse_mode="Markdown")
    return ADD_PROD_DESC

async def _ap_desc(u, c):
    c.user_data["np"]["description"] = u.message.text.strip()
    await u.message.reply_text("✅\n\n*ধাপ ৪:* মূল্য লিখুন (যেমন: 1299):", parse_mode="Markdown")
    return ADD_PROD_PRICE

async def _ap_price(u, c):
    try: c.user_data["np"]["price"] = float(u.message.text.strip())
    except ValueError:
        await u.message.reply_text("⚠️ সঠিক মূল্য দিন:")
        return ADD_PROD_PRICE
    await u.message.reply_text("✅\n\n*ধাপ ৫:* ডিসকাউন্ট মূল্য লিখুন _(না থাকলে 0)_:", parse_mode="Markdown")
    return ADD_PROD_DISC

async def _ap_disc(u, c):
    try: c.user_data["np"]["discount_price"] = float(u.message.text.strip())
    except ValueError: c.user_data["np"]["discount_price"] = 0
    await u.message.reply_text("✅\n\n*ধাপ ৬:* স্টক সংখ্যা লিখুন:", parse_mode="Markdown")
    return ADD_PROD_STOCK

async def _ap_stock(u, c):
    try: c.user_data["np"]["stock"] = int(u.message.text.strip())
    except ValueError:
        await u.message.reply_text("⚠️ সঠিক সংখ্যা দিন:")
        return ADD_PROD_STOCK
    await u.message.reply_text("✅\n\n*ধাপ ৭:* পণ্যের ছবি পাঠান _(না থাকলে skip লিখুন)_:", parse_mode="Markdown")
    return ADD_PROD_IMAGE

async def _ap_image(u, c):
    np = c.user_data["np"]
    image_url = None
    if u.message.photo:
        image_url = u.message.photo[-1].file_id
    elif u.message.text and u.message.text.lower() != "skip":
        image_url = u.message.text.strip()
    pid = add_product(np["name"], np["category"], np["description"],
                      np["price"], np.get("discount_price", 0), np["stock"], image_url)
    await u.message.reply_text(
        f"✅ *পণ্য #{pid} যোগ হয়েছে!*\n📛 {np['name']}\n💰 {format_price(np['price'])}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Dashboard", callback_data="adm_panel")]]))
    c.user_data.pop("np", None)
    return ConversationHandler.END


@admin_only
async def admin_edit_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query      = update.callback_query
    await safe_answer(query)
    parts      = query.data.split("_")   # admprod_<field>_<product_id>
    field      = parts[1]
    product_id = int(parts[2])

    if field == "featured":
        p = get_product(product_id)
        update_product_field(product_id, "is_featured", 0 if p["is_featured"] else 1)
        await query.answer("⭐ Featured টগল হয়েছে!")
        await admin_view_product(update, context)
        return ConversationHandler.END

    if field == "delete":
        soft_delete_product(product_id)
        await safe_edit(query, f"🗑️ পণ্য #{product_id} মুছে ফেলা হয়েছে।",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ পণ্য লিস্ট", callback_data="adm_products_0")]]))
        return ConversationHandler.END

    labels = {"name": "নতুন নাম", "price": "নতুন মূল্য (৳)", "discount": "নতুন ডিসকাউন্ট মূল্য (৳)",
              "stock": "নতুন স্টক সংখ্যা", "image": "নতুন ছবি (পাঠান বা URL)", "desc": "নতুন বিবরণ", "tags": "ট্যাগ (কমা দিয়ে আলাদা)"}
    context.user_data["ep"] = {"field": field, "product_id": product_id}
    await safe_edit(query, f"✏️ *Product #{product_id} সম্পাদনা*\n\n{labels.get(field, field)} লিখুন:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data=f"admprodview_{product_id}")]]))
    return EDIT_PROD_VAL


async def admin_save_product_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ep         = context.user_data.pop("ep", {})
    field      = ep.get("field")
    product_id = ep.get("product_id")
    field_map  = {"name": "name", "price": "price", "discount": "discount_price",
                  "stock": "stock", "image": "image_url", "desc": "description", "tags": "tags"}
    db_field   = field_map.get(field, field)
    value      = None
    if update.message.photo and field == "image":
        value = update.message.photo[-1].file_id
        add_product_image(product_id, value, is_primary=True)
    else:
        value = update.message.text.strip()
        if field in ("price", "discount"):
            try: value = float(value)
            except ValueError:
                await update.message.reply_text("⚠️ সঠিক মূল্য দিন:")
                return EDIT_PROD_VAL
        elif field == "stock":
            try: value = int(value)
            except ValueError:
                await update.message.reply_text("⚠️ সঠিক সংখ্যা দিন:")
                return EDIT_PROD_VAL
    update_product_field(product_id, db_field, value)
    await update.message.reply_text(f"✅ Product #{product_id} আপডেট হয়েছে!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📦 পণ্য দেখুন", callback_data=f"admprodview_{product_id}")]]))
    return ConversationHandler.END


# ════════════════════════════════════════════════
# CATEGORY MANAGEMENT (NEW - full CRUD)
# ════════════════════════════════════════════════

@admin_only
async def admin_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    cats  = get_categories(active_only=False)
    await safe_edit(query, f"🏷️ *ক্যাটাগরি ম্যানেজমেন্ট* ({len(cats)} টি)",
                    reply_markup=admin_categories_keyboard(cats))


@admin_only
async def admin_cat_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await safe_answer(query)
    cat_id = int(query.data.split("_")[-1])
    cat    = get_category(cat_id)
    if not cat:
        await query.answer("❌ ক্যাটাগরি পাওয়া যায়নি!", show_alert=True)
        return
    text = (f"🏷️ *ক্যাটাগরি বিবরণ*\n━━━━━━━━━━━━━━━━━━━━\n"
            f"🆔 ID: {cat['category_id']}\n"
            f"📛 নাম: {cat['name']}\n"
            f"😊 Emoji: {cat['emoji']}\n"
            f"🚦 Status: {'✅ Active' if cat['is_active'] else '❌ Hidden'}\n"
            f"⭐ Featured: {'হ্যাঁ' if cat['is_featured'] else 'না'}")
    await safe_edit(query, text, reply_markup=admin_category_detail_keyboard(cat_id, bool(cat["is_active"]), bool(cat["is_featured"])))


@admin_only
async def admin_cat_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    context.user_data["new_cat"] = {}
    await safe_edit(query, "🏷️ *নতুন ক্যাটাগরি*\n\nক্যাটাগরির নাম লিখুন:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data="adm_categories")]]))
    return ADD_CAT_NAME


async def _cat_name(u, c):
    c.user_data["new_cat"]["name"] = u.message.text.strip()
    await u.message.reply_text("✅\n\nক্যাটাগরির Emoji লিখুন:\n_(যেমন: 👗 বা 📱)_", parse_mode="Markdown")
    return ADD_CAT_EMOJI


async def _cat_emoji(u, c):
    emoji = u.message.text.strip()
    nc    = c.user_data.pop("new_cat", {})
    cid   = add_category(nc["name"], emoji)
    await u.message.reply_text(f"✅ *ক্যাটাগরি '{nc['name']}' যোগ হয়েছে!* (ID: {cid})",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ক্যাটাগরি", callback_data="adm_categories")]]))
    return ConversationHandler.END


@admin_only
async def admin_cat_edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await safe_answer(query)
    parts  = query.data.split("_")  # adm_cat_edit_<field>_<id>
    field  = parts[3]
    cat_id = int(parts[4])
    context.user_data["edit_cat"] = {"field": field, "cat_id": cat_id}
    labels = {"name": "নতুন নাম", "emoji": "নতুন Emoji"}
    await safe_edit(query, f"✏️ ক্যাটাগরি সম্পাদনা\n\n{labels.get(field, field)} লিখুন:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data=f"adm_cat_view_{cat_id}")]]))
    return EDIT_CAT_VAL


async def _cat_edit_save(u, c):
    ec     = c.user_data.pop("edit_cat", {})
    field  = ec.get("field")
    cat_id = ec.get("cat_id")
    update_category(cat_id, field, u.message.text.strip())
    await u.message.reply_text(f"✅ ক্যাটাগরি আপডেট হয়েছে!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ক্যাটাগরি", callback_data="adm_categories")]]))
    return ConversationHandler.END


@admin_only
async def admin_cat_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await safe_answer(query)
    cat_id = int(query.data.split("_")[-1])
    cat    = get_category(cat_id)
    update_category(cat_id, "is_active", 0 if cat["is_active"] else 1)
    await query.answer("✅ স্ট্যাটাস পরিবর্তন হয়েছে!")
    await admin_categories(update, context)


@admin_only
async def admin_cat_feature(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await safe_answer(query)
    cat_id = int(query.data.split("_")[-1])
    cat    = get_category(cat_id)
    update_category(cat_id, "is_featured", 0 if cat["is_featured"] else 1)
    await query.answer("⭐ Featured টগল হয়েছে!")
    await admin_cat_view(update, context)


@admin_only
async def admin_cat_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query  = update.callback_query
    await safe_answer(query)
    cat_id = int(query.data.split("_")[-1])
    delete_category(cat_id)
    await safe_edit(query, "🗑️ ক্যাটাগরি মুছে ফেলা হয়েছে।",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ক্যাটাগরি", callback_data="adm_categories")]]))


# ════════════════════════════════════════════════
# DELIVERY MANAGEMENT (NEW - full CRUD)
# ════════════════════════════════════════════════

@admin_only
async def admin_delivery(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await safe_answer(query)
    methods = get_delivery_methods(active_only=False)
    await safe_edit(query, f"🚚 *ডেলিভারি ম্যানেজমেন্ট* ({len(methods)} টি)",
                    reply_markup=admin_delivery_keyboard(methods))


@admin_only
async def admin_dlv_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await safe_answer(query)
    method_id = int(query.data.split("_")[-1])
    m         = get_delivery_method(method_id)
    if not m:
        await query.answer("❌ পাওয়া যায়নি!", show_alert=True)
        return
    text = (f"🚚 *ডেলিভারি পদ্ধতি*\n━━━━━━━━━━━━━━━━━━━━\n"
            f"📛 নাম: {m['name']}\n"
            f"💰 চার্জ: ৳{int(m['charge'])}\n"
            f"📝 বিবরণ: {m['description']}\n"
            f"💵 COD: {'✅' if m['cod_allowed'] else '❌'}\n"
            f"🚦 Status: {'✅ Active' if m['is_active'] else '❌ Inactive'}")
    await safe_edit(query, text, reply_markup=admin_delivery_detail_keyboard(method_id, bool(m["is_active"])))


@admin_only
async def admin_dlv_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    context.user_data["nd"] = {}
    await safe_edit(query, "🚚 *নতুন ডেলিভারি পদ্ধতি*\n\nপদ্ধতির নাম লিখুন:\n_(যেমন: Inside Dhaka)_",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data="adm_delivery")]]))
    return ADD_DLV_NAME


async def _dlv_name(u, c):
    c.user_data["nd"]["name"] = u.message.text.strip()
    await u.message.reply_text("✅\n\nবিবরণ লিখুন:\n_(যেমন: ঢাকার ভেতরে ১-২ দিন)_", parse_mode="Markdown")
    return ADD_DLV_DESC

async def _dlv_desc(u, c):
    c.user_data["nd"]["description"] = u.message.text.strip()
    await u.message.reply_text("✅\n\nডেলিভারি চার্জ লিখুন (৳):\n_(বিনামূল্যে হলে 0)_", parse_mode="Markdown")
    return ADD_DLV_CHARGE

async def _dlv_charge(u, c):
    try: charge = float(u.message.text.strip())
    except ValueError:
        await u.message.reply_text("⚠️ সঠিক সংখ্যা দিন:")
        return ADD_DLV_CHARGE
    nd  = c.user_data.pop("nd", {})
    mid = add_delivery_method(nd["name"], nd["description"], charge)
    await u.message.reply_text(f"✅ *'{nd['name']}' যোগ হয়েছে!*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ডেলিভারি", callback_data="adm_delivery")]]))
    return ConversationHandler.END


@admin_only
async def admin_dlv_edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await safe_answer(query)
    parts     = query.data.split("_")  # adm_dlv_edit_<field>_<id>
    field     = parts[3]
    method_id = int(parts[4])
    context.user_data["ed"] = {"field": field, "method_id": method_id}
    labels = {"name": "নতুন নাম", "charge": "নতুন চার্জ (৳)"}
    await safe_edit(query, f"✏️ ডেলিভারি সম্পাদনা\n\n{labels.get(field, field)} লিখুন:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data=f"adm_dlv_view_{method_id}")]]))
    return EDIT_DLV_VAL

async def _dlv_edit_save(u, c):
    ed        = c.user_data.pop("ed", {})
    field     = ed.get("field")
    method_id = ed.get("method_id")
    value     = u.message.text.strip()
    if field == "charge":
        try: value = float(value)
        except ValueError:
            await u.message.reply_text("⚠️ সঠিক সংখ্যা দিন:")
            return EDIT_DLV_VAL
    update_delivery_method(method_id, field, value)
    await u.message.reply_text("✅ আপডেট হয়েছে!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ডেলিভারি", callback_data="adm_delivery")]]))
    return ConversationHandler.END


@admin_only
async def admin_dlv_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await safe_answer(query)
    method_id = int(query.data.split("_")[-1])
    m         = get_delivery_method(method_id)
    update_delivery_method(method_id, "is_active", 0 if m["is_active"] else 1)
    await query.answer("✅ স্ট্যাটাস পরিবর্তন!")
    await admin_delivery(update, context)


@admin_only
async def admin_dlv_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await safe_answer(query)
    method_id = int(query.data.split("_")[-1])
    delete_delivery_method(method_id)
    await safe_edit(query, "🗑️ ডেলিভারি পদ্ধতি মুছে ফেলা হয়েছে।",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ ডেলিভারি", callback_data="adm_delivery")]]))


# ════════════════════════════════════════════════
# PAYMENT METHOD MANAGEMENT (NEW)
# ════════════════════════════════════════════════

@admin_only
async def admin_payment_methods(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await safe_answer(query)
    methods = get_payment_methods(active_only=False)
    await safe_edit(query, f"💳 *পেমেন্ট পদ্ধতি* ({len(methods)} টি)",
                    reply_markup=admin_payment_methods_keyboard(methods))


@admin_only
async def admin_pm_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await safe_answer(query)
    method_id = int(query.data.split("_")[-1])
    m         = get_payment_method(method_id)
    if not m:
        await query.answer("❌ পাওয়া যায়নি!", show_alert=True)
        return
    text = (f"💳 *পেমেন্ট পদ্ধতি বিবরণ*\n━━━━━━━━━━━━━━━━━━━━\n"
            f"{m['emoji']} নাম: {m['name']}\n"
            f"📱 নম্বর: {m['number'] or '—'}\n"
            f"📝 বিবরণ: {m['description']}\n"
            f"💵 COD: {'হ্যাঁ' if m['is_cod'] else 'না'}\n"
            f"🚦 Status: {'✅ Active' if m['is_active'] else '❌ Inactive'}")
    await safe_edit(query, text, reply_markup=admin_payment_detail_keyboard(method_id, bool(m["is_active"])))


@admin_only
async def admin_pm_edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await safe_answer(query)
    parts     = query.data.split("_")  # adm_pm_edit_<field>_<id>
    field     = parts[3]
    method_id = int(parts[4])
    context.user_data["epm"] = {"field": field, "method_id": method_id}
    labels = {"name": "নতুন নাম", "number": "নতুন নম্বর"}
    await safe_edit(query, f"✏️ পেমেন্ট পদ্ধতি সম্পাদনা\n\n{labels.get(field, field)} লিখুন:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data=f"adm_pm_view_{method_id}")]]))
    return EDIT_PM_VAL

async def _pm_edit_save(u, c):
    epm       = c.user_data.pop("epm", {})
    method_id = epm.get("method_id")
    field     = epm.get("field")
    update_payment_method(method_id, field, u.message.text.strip())
    await u.message.reply_text("✅ পেমেন্ট পদ্ধতি আপডেট হয়েছে!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ পেমেন্ট", callback_data="adm_payment_methods")]]))
    return ConversationHandler.END


@admin_only
async def admin_pm_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await safe_answer(query)
    method_id = int(query.data.split("_")[-1])
    m         = get_payment_method(method_id)
    update_payment_method(method_id, "is_active", 0 if m["is_active"] else 1)
    await query.answer("✅ স্ট্যাটাস পরিবর্তন!")
    await admin_payment_methods(update, context)


@admin_only
async def admin_pm_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    context.user_data["npm"] = {}
    await safe_edit(query, "💳 *নতুন পেমেন্ট পদ্ধতি*\n\nনাম লিখুন:\n_(যেমন: bKash)_",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data="adm_payment_methods")]]))
    return ADD_PM_NAME

async def _pm_name(u, c):
    c.user_data["npm"]["name"] = u.message.text.strip()
    await u.message.reply_text("✅\n\nনম্বর লিখুন:\n_(না থাকলে skip)_", parse_mode="Markdown")
    return ADD_PM_NUM

async def _pm_num(u, c):
    txt = u.message.text.strip()
    c.user_data["npm"]["number"] = "" if txt.lower() == "skip" else txt
    await u.message.reply_text("✅\n\nবিবরণ লিখুন:\n_(যেমন: Send Money করুন)_", parse_mode="Markdown")
    return ADD_PM_DESC

async def _pm_desc(u, c):
    npm = c.user_data.pop("npm", {})
    npm["description"] = u.message.text.strip()
    mid = add_payment_method(npm["name"], npm.get("number", ""), npm["description"])
    await u.message.reply_text(f"✅ *'{npm['name']}' পেমেন্ট পদ্ধতি যোগ হয়েছে!*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ পেমেন্ট", callback_data="adm_payment_methods")]]))
    return ConversationHandler.END


# ════════════════════════════════════════════════
# COUPON MANAGEMENT (full CRUD with edit/delete)
# ════════════════════════════════════════════════

@admin_only
async def admin_coupons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await safe_answer(query)
    coupons = get_all_coupons()
    if not coupons:
        await safe_edit(query, "🎫 *কুপন*\n\nকোনো কুপন নেই।",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("➕ নতুন কুপন", callback_data="adm_coupon_add")],
                [InlineKeyboardButton("⬅️ Dashboard", callback_data="adm_panel")],
            ]))
        return
    await safe_edit(query, f"🎫 *কুপন ম্যানেজমেন্ট* ({len(coupons)} টি)",
                    reply_markup=admin_coupons_keyboard(coupons))


@admin_only
async def admin_coupon_view(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await safe_answer(query)
    coupon_id = int(query.data.split("_")[-1])
    c         = get_coupon(coupon_id)
    if not c:
        await query.answer("❌ কুপন পাওয়া যায়নি!", show_alert=True)
        return
    disc = f"{c['discount_val']}%" if c["discount_type"] == "percent" else f"৳{int(c['discount_val'])}"
    exp  = str(c["expires_at"])[:10] if c["expires_at"] else "মেয়াদ নেই"
    text = (f"🎫 *কুপন বিবরণ*\n━━━━━━━━━━━━━━━━━━━━\n"
            f"কোড: `{c['code']}`\n"
            f"ডিসকাউন্ট: {disc}\n"
            f"ন্যূনতম অর্ডার: ৳{int(c['min_order'])}\n"
            f"ব্যবহার: {c['used_count']}/{c['max_uses']}\n"
            f"মেয়াদ: {exp}\n"
            f"স্ট্যাটাস: {'✅ Active' if c['is_active'] else '❌ Inactive'}")
    await safe_edit(query, text, reply_markup=admin_coupon_detail_keyboard(coupon_id, bool(c["is_active"])))


@admin_only
async def admin_coupon_add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    context.user_data["nc"] = {}
    await safe_edit(query, "🎫 *নতুন কুপন*\n\nকুপন কোড লিখুন:\n_(যেমন: SUMMER20)_",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data="adm_coupons")]]))
    return ADD_CPN_CODE

async def _cpn_code(u, c):
    c.user_data["nc"]["code"] = u.message.text.strip().upper()
    await u.message.reply_text("✅\n\nডিসকাউন্ট ধরন লিখুন:\n*percent* বা *flat*", parse_mode="Markdown")
    return ADD_CPN_TYPE

async def _cpn_type(u, c):
    t = u.message.text.strip().lower()
    if t not in ("percent", "flat"):
        await u.message.reply_text("⚠️ *percent* বা *flat* লিখুন:", parse_mode="Markdown")
        return ADD_CPN_TYPE
    c.user_data["nc"]["discount_type"] = t
    label = "শতাংশ (যেমন: 10)" if t == "percent" else "টাকার পরিমাণ (যেমন: 50)"
    await u.message.reply_text(f"✅\n\nডিসকাউন্ট পরিমাণ লিখুন ({label}):", parse_mode="Markdown")
    return ADD_CPN_VAL

async def _cpn_val(u, c):
    try: c.user_data["nc"]["discount_val"] = float(u.message.text.strip())
    except ValueError:
        await u.message.reply_text("⚠️ সঠিক সংখ্যা দিন:")
        return ADD_CPN_VAL
    await u.message.reply_text("✅\n\nন্যূনতম অর্ডার পরিমাণ লিখুন (৳):\n_(না থাকলে 0)_", parse_mode="Markdown")
    return ADD_CPN_MIN

async def _cpn_min(u, c):
    try: c.user_data["nc"]["min_order"] = float(u.message.text.strip())
    except ValueError: c.user_data["nc"]["min_order"] = 0
    await u.message.reply_text("✅\n\nমেয়াদ শেষের তারিখ লিখুন:\n_(Format: 2025-12-31 — না থাকলে skip)_", parse_mode="Markdown")
    return ADD_CPN_EXP

async def _cpn_exp(u, c):
    txt = u.message.text.strip()
    nc  = c.user_data.pop("nc", {})
    exp = None if txt.lower() == "skip" else txt
    create_coupon(nc["code"], nc.get("discount_type", "percent"), nc.get("discount_val", 0),
                  nc.get("min_order", 0), 1000, exp)
    await u.message.reply_text(f"✅ *কুপন '{nc['code']}' তৈরি হয়েছে!*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ কুপন", callback_data="adm_coupons")]]))
    return ConversationHandler.END


@admin_only
async def admin_coupon_edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await safe_answer(query)
    parts     = query.data.split("_")  # adm_coupon_edit_<field>_<id>
    field     = parts[3]
    coupon_id = int(parts[4])
    context.user_data["ecpn"] = {"field": field, "coupon_id": coupon_id}
    labels = {"code": "নতুন কোড", "val": "নতুন পরিমাণ", "exp": "নতুন মেয়াদ (YYYY-MM-DD)"}
    await safe_edit(query, f"✏️ কুপন সম্পাদনা\n\n{labels.get(field, field)} লিখুন:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data=f"adm_coupon_view_{coupon_id}")]]))
    return EDIT_CPN_VAL

async def _cpn_edit_save(u, c):
    ec        = c.user_data.pop("ecpn", {})
    field     = ec.get("field")
    coupon_id = ec.get("coupon_id")
    db_map    = {"code": "code", "val": "discount_val", "exp": "expires_at"}
    db_field  = db_map.get(field, field)
    value     = u.message.text.strip()
    if field == "val":
        try: value = float(value)
        except ValueError:
            await u.message.reply_text("⚠️ সঠিক সংখ্যা দিন:")
            return EDIT_CPN_VAL
    update_coupon(coupon_id, db_field, value)
    await u.message.reply_text("✅ কুপন আপডেট হয়েছে!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ কুপন", callback_data="adm_coupons")]]))
    return ConversationHandler.END


@admin_only
async def admin_coupon_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await safe_answer(query)
    coupon_id = int(query.data.split("_")[-1])
    cp        = get_coupon(coupon_id)
    update_coupon(coupon_id, "is_active", 0 if cp["is_active"] else 1)
    await query.answer("✅ কুপন স্ট্যাটাস পরিবর্তন!")
    await admin_coupons(update, context)


@admin_only
async def admin_coupon_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await safe_answer(query)
    coupon_id = int(query.data.split("_")[-1])
    delete_coupon(coupon_id)
    await safe_edit(query, "🗑️ কুপন মুছে ফেলা হয়েছে।",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ কুপন", callback_data="adm_coupons")]]))


# ════════════════════════════════════════════════
# BROADCAST (all + single user)
# ════════════════════════════════════════════════

@admin_only
async def admin_broadcast_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    await safe_edit(query, "📢 *ব্রডকাস্ট সিস্টেম*\n\nকী করতে চান?",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 সবাইকে পাঠান",      callback_data="adm_broadcast_all")],
            [InlineKeyboardButton("✉️ একজনকে পাঠান",     callback_data="adm_msg_user")],
            [InlineKeyboardButton("⬅️ Dashboard",         callback_data="adm_panel")],
        ]))


@admin_only
async def admin_broadcast_all_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    await safe_edit(query, "📢 *সব ইউজারকে ব্রডকাস্ট*\n\nপাঠানোর বার্তা লিখুন:\n_(Markdown সমর্থিত)_",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data="adm_panel")]]))
    return BROADCAST_MSG


@admin_only
async def admin_broadcast_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg_text = update.message.text
    user_ids = get_all_user_ids()
    status   = await update.message.reply_text(f"📢 {len(user_ids)} জনকে পাঠানো হচ্ছে...")
    sent = failed = 0
    for uid in user_ids:
        try:
            await context.bot.send_message(
                chat_id=uid,
                text=f"📢 *{BOT_NAME_BROADCAST} — বিশেষ বার্তা*\n\n{msg_text}",
                parse_mode="Markdown")
            sent += 1
        except Exception:
            failed += 1
    await status.edit_text(
        f"✅ *ব্রডকাস্ট সম্পন্ন!*\n✔️ পাঠানো: {sent}\n❌ ব্যর্থ: {failed}",
        parse_mode="Markdown")
    return ConversationHandler.END


# inject bot name without circular import
try:
    from config.settings import BOT_NAME as BOT_NAME_BROADCAST
except ImportError:
    BOT_NAME_BROADCAST = "PickDeal BD"


@admin_only
async def admin_msg_user_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    await safe_edit(query, "✉️ *একজন ইউজারকে মেসেজ*\n\nইউজারের Telegram ID লিখুন:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data="adm_panel")]]))
    return MSG_USER_ID


async def _msg_user_id(u, c):
    txt = u.message.text.strip()
    if not txt.isdigit():
        await u.message.reply_text("⚠️ শুধু সংখ্যা দিন:")
        return MSG_USER_ID
    c.user_data["msg_target_id"] = int(txt)
    user = get_user(int(txt))
    name = user["first_name"] if user else "Unknown"
    await u.message.reply_text(
        f"✅ ইউজার: *{name}* (ID: {txt})\n\nপাঠানোর বার্তা লিখুন:",
        parse_mode="Markdown")
    return MSG_USER_TEXT


async def _msg_user_text(u, c):
    target_id = c.user_data.pop("msg_target_id", None)
    if not target_id:
        return ConversationHandler.END
    sent = await notify_user(c, target_id, f"📩 *Admin বার্তা:*\n\n{u.message.text}", parse_mode="Markdown")
    await u.message.reply_text(
        f"{'✅ বার্তা পাঠানো হয়েছে!' if sent else '❌ পাঠানো ব্যর্থ (ব্লক হতে পারে)।'}",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Dashboard", callback_data="adm_panel")]]))
    return ConversationHandler.END


# ════════════════════════════════════════════════
# ANALYTICS & CUSTOMERS
# ════════════════════════════════════════════════

@admin_only
async def admin_analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await safe_answer(query)
    stats    = get_revenue_stats()
    counts   = count_orders_by_status()
    users    = get_user_count()
    top_prod = get_top_products(5)
    daily    = get_daily_stats(7)
    await safe_edit(query, format_analytics(stats, counts, users, top_prod, daily),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Dashboard", callback_data="adm_panel")]]))


@admin_only
async def admin_customers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    top   = get_top_customers(10)
    total = get_user_count()
    lines = [f"👥 *কাস্টমার ওভারভিউ*\nমোট ইউজার: *{total:,}*\n━━━━━━━━━━━━━━━━━━━━\n🏆 *টপ কাস্টমার (User ID সহ):*"]
    for i, cu in enumerate(top, 1):
        try:
            uname  = cu["username"] or ""
            fname  = cu["first_name"] or "User"
            uid    = cu["user_id"]
            spent  = float(cu["total_spent"] or 0)
            orders = int(cu["total_orders"] or 0)
            dname  = f"@{uname}" if uname else fname
            lines.append(f"{i}. {dname} | ID:`{uid}` | {orders} অর্ডার | {format_price(spent)}")
        except Exception:
            lines.append(f"{i}. data error")
    await safe_edit(query, "\n".join(lines),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Dashboard", callback_data="adm_panel")]]))


@admin_only
async def admin_low_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    prods = get_low_stock_products(threshold=10)
    if not prods:
        await safe_edit(query, "✅ *কম স্টক নেই!* সব পণ্যের স্টক ঠিক আছে।",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Dashboard", callback_data="adm_panel")]]))
        return
    lines = ["⚠️ *কম স্টক অ্যালার্ট*\n"]
    for p in prods:
        icon = "❌" if p["stock"] == 0 else "⚠️"
        lines.append(f"{icon} *{p['name'][:28]}* — {p['stock']} টি বাকি")
    await safe_edit(query, "\n".join(lines),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 পণ্য লিস্ট", callback_data="adm_products_0")],
            [InlineKeyboardButton("⬅️ Dashboard",   callback_data="adm_panel")],
        ]))


# ════════════════════════════════════════════════
# SUPPORT TICKETS (admin side) — FIX: Open Tickets
# ════════════════════════════════════════════════

@admin_only
async def admin_view_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    FIX v3: adm_tickets_<page> pattern. Old v2 had wrong callback name.
    Now correctly fetches open tickets and shows them.
    """
    query = update.callback_query
    await safe_answer(query)
    page    = int(query.data.split("_")[-1])
    tickets = get_open_tickets(limit=PAGE + page * PAGE)

    if not tickets:
        await safe_edit(query, "🎫 *Open Tickets*\n\nকোনো খোলা টিকেট নেই! ✅",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Dashboard", callback_data="adm_panel")]]))
        return

    buttons = []
    for t in tickets:
        name  = t["first_name"] or "User"
        label = f"#{t['ticket_id']} | {name[:8]} | {str(t['message'])[:25]}..."
        buttons.append([InlineKeyboardButton(label, callback_data=f"adm_ticket_view_{t['ticket_id']}")])
    buttons.append([InlineKeyboardButton("⬅️ Dashboard", callback_data="adm_panel")])
    await safe_edit(query, f"🎫 *Open Tickets* ({len(tickets)} টি)",
                    reply_markup=InlineKeyboardMarkup(buttons))


@admin_only
async def admin_ticket_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await safe_answer(query)
    ticket_id = int(query.data.split("_")[-1])
    t         = get_ticket(ticket_id)
    if not t:
        await query.answer("❌ Ticket পাওয়া যায়নি!", show_alert=True)
        return
    uname = f"@{t['username']}" if t["username"] else t["first_name"]
    text  = (f"🎫 *Ticket #{ticket_id}*\n"
             f"👤 {uname} | ID: {t['user_id']}\n"
             f"📅 {str(t['created_at'])[:16]}\n"
             f"━━━━━━━━━━━━━━━━━━━━\n"
             f"💬 {t['message']}\n")
    try:
        reply = t["reply"]
    except Exception:
        reply = None
    if reply:
        text += f"━━━━━━━━━━━━━━━━━━━━\n📩 *উত্তর:* {reply}"
    await safe_edit(query, text, reply_markup=admin_ticket_keyboard(ticket_id, t["status"]))


@admin_only
async def admin_ticket_reply_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await safe_answer(query)
    ticket_id = int(query.data.split("_")[-1])
    context.user_data["reply_ticket_id"] = ticket_id
    await safe_edit(query, f"📩 *Ticket #{ticket_id} উত্তর*\n\nআপনার উত্তর লিখুন:",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ বাতিল", callback_data="adm_tickets_0")]]))
    return TICKET_REPLY_STATE


@admin_only
async def admin_ticket_reply_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ticket_id = context.user_data.pop("reply_ticket_id", None)
    if not ticket_id:
        return ConversationHandler.END
    t = get_ticket(ticket_id)
    reply_ticket(ticket_id, update.message.text.strip(), update.effective_user.id)
    if t:
        await notify_user(context, t["user_id"],
            f"📩 *সাপোর্ট উত্তর — Ticket #{ticket_id}*\n\n"
            f"PickDeal BD সাপোর্ট টিমের উত্তর:\n\n{update.message.text.strip()}",
            parse_mode="Markdown")
    await update.message.reply_text(f"✅ Ticket #{ticket_id} উত্তর পাঠানো হয়েছে!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Tickets", callback_data="adm_tickets_0")]]))
    return ConversationHandler.END


@admin_only
async def admin_ticket_close(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await safe_answer(query)
    ticket_id = int(query.data.split("_")[-1])
    set_ticket_status(ticket_id, "closed")
    await query.answer(f"✅ Ticket #{ticket_id} বন্ধ করা হয়েছে!")
    await admin_view_tickets(update, context)


@admin_only
async def admin_ticket_reopen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query     = update.callback_query
    await safe_answer(query)
    ticket_id = int(query.data.split("_")[-1])
    set_ticket_status(ticket_id, "open")
    await query.answer(f"🔄 Ticket #{ticket_id} পুনরায় খোলা হয়েছে!")
    await admin_view_tickets(update, context)
