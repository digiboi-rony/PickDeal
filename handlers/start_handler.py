"""
handlers/start_handler.py — v3.2 FIXED
BUG FIX: t.get("reply") → t["reply"] with try/except for sqlite3.Row
NEW: Review system after delivery
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database.queries import (
    upsert_user, get_user, get_wishlist, get_recently_viewed,
    add_to_wishlist, remove_from_wishlist, is_in_wishlist,
    search_products, get_user_orders, get_user_tickets,
)
from keyboards.builder import (
    main_menu_keyboard, profile_keyboard, wishlist_keyboard,
    support_keyboard, back_to_menu, order_list_keyboard, review_keyboard,
)
from utils.helpers import safe_edit, safe_answer, ban_check
from utils.formatters import format_profile, format_price
from config.settings import BOT_NAME

logger = logging.getLogger(__name__)
SEARCH_INPUT = 99
REVIEW_TEXT  = 98


def _g(row, key, default=None):
    try:
        v = row[key]
        return v if v is not None else default
    except (KeyError, IndexError, TypeError):
        return default


def _welcome_text(first_name: str) -> str:
    return (
        f"🎉 *আসসালামু আলাইকুম, {first_name}!*\n\n"
        f"*{BOT_NAME}* — বাংলাদেশের সেরা অনলাইন শপিং বটে স্বাগতম! 🇧🇩\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🛍️ হাজারো পণ্য, সেরা দাম\n"
        f"🚚 সারাদেশে দ্রুত ডেলিভারি\n"
        f"💳 bKash • Nagad • ক্যাশ অন ডেলিভারি\n"
        f"🔒 নিরাপদ ও বিশ্বস্ত শপিং\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👇 নিচের বাটন থেকে শুরু করুন:"
    )


@ban_check
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    upsert_user(user.id, user.username or "", user.first_name or "", user.last_name or "")
    logger.info(f"/start — user {user.id} ({user.first_name})")
    await update.message.reply_text(
        _welcome_text(user.first_name or "বন্ধু"),
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    user = update.effective_user
    await safe_edit(query, _welcome_text(user.first_name or "বন্ধু"), reply_markup=main_menu_keyboard())


async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    user_id = update.effective_user.id
    user    = get_user(user_id)
    orders  = get_user_orders(user_id, limit=5)
    await safe_edit(query, format_profile(user, orders), reply_markup=profile_keyboard())


async def my_wishlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await safe_answer(query)
    user_id  = update.effective_user.id
    products = get_wishlist(user_id)
    if not products:
        await safe_edit(query,
            "❤️ *উইশলিস্ট*\n\nআপনার উইশলিস্ট খালি!\nপছন্দের পণ্যে ❤️ বাটন চাপুন।",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍️ পণ্য দেখুন", callback_data="browse_categories")],
                [InlineKeyboardButton("🏠 মেইন মেনু",  callback_data="main_menu")],
            ]))
        return
    await safe_edit(query, f"❤️ *উইশলিস্ট* ({len(products)} টি পণ্য)",
                    reply_markup=wishlist_keyboard(products))


async def toggle_wishlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query      = update.callback_query
    user_id    = update.effective_user.id
    product_id = int(query.data.split("_")[1])
    if is_in_wishlist(user_id, product_id):
        remove_from_wishlist(user_id, product_id)
        await query.answer("💔 উইশলিস্ট থেকে সরানো হয়েছে")
    else:
        add_to_wishlist(user_id, product_id)
        await query.answer("❤️ উইশলিস্টে যোগ হয়েছে!")
    from handlers.product_handler import _show_product
    await _show_product(update, context, product_id)


async def recently_viewed_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await safe_answer(query)
    user_id  = update.effective_user.id
    products = get_recently_viewed(user_id, limit=8)
    if not products:
        await safe_edit(query, "🕐 *সম্প্রতি দেখা*\n\nকোনো পণ্য দেখেননি।", reply_markup=back_to_menu())
        return
    buttons = [[InlineKeyboardButton(
        f"🕐 {_g(p,'name','পণ্য')[:26]} | {format_price(_g(p,'discount_price') or _g(p,'price',0))}",
        callback_data=f"product_{_g(p,'product_id',0)}"
    )] for p in products]
    buttons.append([InlineKeyboardButton("🏠 মেইন মেনু", callback_data="main_menu")])
    await safe_edit(query, f"🕐 *সম্প্রতি দেখা* ({len(products)} টি)",
                    reply_markup=InlineKeyboardMarkup(buttons))


async def search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    await safe_edit(query,
        "🔎 *পণ্য সার্চ*\n\nপণ্যের নাম বা কীওয়ার্ড লিখুন:\n_(যেমন: shirt, watch, umbrella)_",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ বাতিল", callback_data="main_menu")
        ]]))
    return SEARCH_INPUT


async def handle_search_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.message.text.strip()
    if not q:
        await update.message.reply_text("⚠️ সার্চ কীওয়ার্ড লিখুন।")
        return SEARCH_INPUT
    results = search_products(q, limit=10)
    if not results:
        await update.message.reply_text(
            f"😔 *'{q}'* — কোনো পণ্য পাওয়া যায়নি।",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 মেইন মেনু", callback_data="main_menu")
            ]]))
        return ConversationHandler.END
    buttons = []
    for p in results:
        price = format_price(_g(p, "discount_price") or _g(p, "price", 0))
        icon  = "✅" if int(_g(p, "stock", 0) or 0) > 0 else "❌"
        buttons.append([InlineKeyboardButton(
            f"{icon} {_g(p,'name','?')[:26]} — {price}",
            callback_data=f"product_{_g(p,'product_id',0)}"
        )])
    buttons.append([InlineKeyboardButton("🏠 মেইন মেনু", callback_data="main_menu")])
    await update.message.reply_text(
        f"🔎 *'{q}'* — {len(results)} টি পণ্য পাওয়া গেছে:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons))
    return ConversationHandler.END


async def customer_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    await safe_edit(query,
        "💬 *Customer Support*\n\nআমরা সবসময় আপনার পাশে আছি! 🤝\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📞 *সাপোর্ট সময়:* সকাল ৯টা — রাত ৯টা\n"
        "⏱️ *উত্তর সময়:* ১–৩ ঘণ্টার মধ্যে\n"
        "━━━━━━━━━━━━━━━━━━━━",
        reply_markup=support_keyboard())


async def my_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """FIXED: sqlite3.Row has no .get() — use _g() helper."""
    query   = update.callback_query
    await safe_answer(query)
    user_id = update.effective_user.id
    tickets = get_user_tickets(user_id)
    if not tickets:
        await safe_edit(query,
            "🎫 *আমার টিকেট*\n\nআপনার কোনো সাপোর্ট টিকেট নেই।",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🆕 নতুন টিকেট", callback_data="new_ticket")],
                [InlineKeyboardButton("🏠 মেইন মেনু",  callback_data="main_menu")],
            ]))
        return
    STATUS_MAP = {
        "open": "🔴 Open", "in_progress": "🟡 চলছে",
        "resolved": "🟢 সমাধান", "closed": "⚫ বন্ধ",
    }
    lines = ["🎫 *আমার সাপোর্ট টিকেট*\n"]
    for t in tickets:
        status  = _g(t, "status", "open")
        st      = STATUS_MAP.get(status, status)
        created = str(_g(t, "created_at", ""))[:16]
        msg     = str(_g(t, "message", "") or "")[:80]
        tid     = _g(t, "ticket_id", "?")
        lines.append(
            f"━━━━━━━━━━\n"
            f"🎫 Ticket #{tid} | {st}\n"
            f"📅 {created}\n"
            f"💬 {msg}{'...' if len(msg) >= 80 else ''}\n"
        )
        reply = _g(t, "reply")
        if reply:
            lines.append(f"📩 *উত্তর:* {str(reply)[:120]}\n")
    await safe_edit(query, "\n".join(lines),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🆕 নতুন টিকেট", callback_data="new_ticket")],
            [InlineKeyboardButton("🏠 মেইন মেনু",  callback_data="main_menu")],
        ]))


# ── Review System ─────────────────────────────────────────────────

async def review_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User clicks ⭐ রিভিউ দিন after delivery."""
    query    = update.callback_query
    await safe_answer(query)
    order_id = int(query.data.split("_")[1])
    context.user_data["review_order_id"] = order_id
    await safe_edit(query,
        f"⭐ *অর্ডার #{order_id} রিভিউ*\n\n"
        f"আপনার অর্ডার সম্পর্কে রেটিং দিন:\n",
        reply_markup=review_keyboard(order_id))


async def review_star(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """User selects star rating: rev_<order_id>_<stars>"""
    query    = update.callback_query
    await safe_answer(query)
    parts    = query.data.split("_")
    order_id = int(parts[1])
    stars    = int(parts[2])
    context.user_data["review_stars"]    = stars
    context.user_data["review_order_id"] = order_id
    star_display = "⭐" * stars
    await safe_edit(query,
        f"⭐ *রেটিং: {star_display} ({stars}/5)*\n\n"
        f"আপনার মতামত লিখুন:\n_(না লিখতে চাইলে *skip* লিখুন)_",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ বাতিল", callback_data="my_orders")
        ]]))
    return REVIEW_TEXT


async def review_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive review text and save."""
    from database.queries import get_order, get_order_items, update_product_field, log_event
    text     = update.message.text.strip()
    stars    = context.user_data.get("review_stars", 5)
    order_id = context.user_data.get("review_order_id")

    if not order_id:
        await update.message.reply_text("⚠️ Session শেষ। /start দিন।")
        return ConversationHandler.END

    review_note = None if text.lower() == "skip" else text

    # Update product ratings from this order
    try:
        items = get_order_items(order_id)
        for item in items:
            pid = _g(item, "product_id")
            if pid:
                p = __import__('database.queries', fromlist=['get_product']).get_product(pid)
                if p:
                    old_rating = float(_g(p, "rating", 0) or 0)
                    old_count  = int(_g(p, "review_count", 0) or 0)
                    new_count  = old_count + 1
                    new_rating = round(((old_rating * old_count) + stars) / new_count, 1)
                    update_product_field(pid, "rating", new_rating)
        log_event("review_submitted", user_id=update.effective_user.id, order_id=order_id, value=stars)
    except Exception as e:
        logger.error(f"Review save error: {e}")

    star_display = "⭐" * stars
    await update.message.reply_text(
        f"✅ *রিভিউ জমা হয়েছে!*\n\n"
        f"⭐ রেটিং: {star_display} ({stars}/5)\n"
        f"{'💬 মতামত: ' + review_note if review_note else ''}\n\n"
        f"আপনার মতামতের জন্য ধন্যবাদ! 🙏",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🛍️ আরো কেনাকাটা", callback_data="browse_categories")],
            [InlineKeyboardButton("🏠 মেইন মেনু",     callback_data="main_menu")],
        ]))
    context.user_data.pop("review_stars", None)
    context.user_data.pop("review_order_id", None)
    return ConversationHandler.END


async def noop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_answer(update.callback_query)
