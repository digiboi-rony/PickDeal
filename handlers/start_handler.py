"""
handlers/start_handler.py — PickDeal BD v3
/start, main menu, profile, wishlist, recently viewed, search, support.
FIX: search ConversationHandler now correctly returns states.
FIX: my_tickets correctly fetches from DB and shows results.
FIX: support handler uses correct back callback.
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
    support_keyboard, back_to_menu, order_list_keyboard,
)
from utils.helpers import safe_edit, safe_answer, ban_check
from utils.formatters import format_profile, format_price
from config.settings import BOT_NAME

logger = logging.getLogger(__name__)

SEARCH_INPUT = 99   # unique state — no conflict with other handlers


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
    await safe_edit(query, _welcome_text(user.first_name or "বন্ধু"),
                    reply_markup=main_menu_keyboard())


# ── Profile ──────────────────────────────────────────────────────

async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    user_id = update.effective_user.id
    user    = get_user(user_id)
    orders  = get_user_orders(user_id, limit=5)
    await safe_edit(query, format_profile(user, orders), reply_markup=profile_keyboard())


# ── Wishlist ─────────────────────────────────────────────────────

async def my_wishlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await safe_answer(query)
    user_id = update.effective_user.id
    products = get_wishlist(user_id)
    if not products:
        await safe_edit(query,
            "❤️ *উইশলিস্ট*\n\nআপনার উইশলিস্ট খালি!\n\nপছন্দের পণ্যে ❤️ বাটন চাপুন।",
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


# ── Recently Viewed ───────────────────────────────────────────────

async def recently_viewed_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await safe_answer(query)
    user_id  = update.effective_user.id
    products = get_recently_viewed(user_id, limit=8)
    if not products:
        await safe_edit(query,
            "🕐 *সম্প্রতি দেখা*\n\nআপনি এখনো কোনো পণ্য দেখেননি।",
            reply_markup=back_to_menu())
        return
    buttons = [[InlineKeyboardButton(
        f"🕐 {p['name'][:26]} | {format_price(p['discount_price'] or p['price'])}",
        callback_data=f"product_{p['product_id']}"
    )] for p in products]
    buttons.append([InlineKeyboardButton("🏠 মেইন মেনু", callback_data="main_menu")])
    await safe_edit(query, f"🕐 *সম্প্রতি দেখা* ({len(products)} টি)",
                    reply_markup=InlineKeyboardMarkup(buttons))


# ── Search  (FIX: proper ConversationHandler entry point) ────────

async def search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    FIX v3: search_prompt now correctly returns SEARCH_INPUT state.
    Old v2 the state was not flowing properly — message handler intercepted first.
    """
    query = update.callback_query
    await safe_answer(query)
    await safe_edit(query,
        "🔎 *পণ্য সার্চ*\n\n"
        "পণ্যের নাম বা কীওয়ার্ড লিখুন:\n"
        "_(যেমন: shirt, watch, umbrella, ছাতা)_",
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
            f"😔 *'{q}'* — কোনো পণ্য পাওয়া যায়নি।\n\nঅন্য কীওয়ার্ড চেষ্টা করুন:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 মেইন মেনু", callback_data="main_menu")
            ]]))
        return ConversationHandler.END

    buttons = []
    for p in results:
        price      = format_price(p["discount_price"] or p["price"])
        stock_icon = "✅" if p["stock"] > 0 else "❌"
        buttons.append([InlineKeyboardButton(
            f"{stock_icon} {p['name'][:26]} — {price}",
            callback_data=f"product_{p['product_id']}"
        )])
    buttons.append([InlineKeyboardButton("🏠 মেইন মেনু", callback_data="main_menu")])
    await update.message.reply_text(
        f"🔎 *'{q}'* — {len(results)} টি পণ্য পাওয়া গেছে:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons))
    return ConversationHandler.END


# ── Support + Tickets ─────────────────────────────────────────────

async def customer_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    await safe_edit(query,
        "💬 *Customer Support*\n\n"
        "আমরা সবসময় আপনার পাশে আছি! 🤝\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📞 *সাপোর্ট সময়:* সকাল ৯টা — রাত ৯টা\n"
        "⏱️ *উত্তর সময়:* ১–৩ ঘণ্টার মধ্যে\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "নতুন টিকেট খুলুন বা আগের টিকেট দেখুন:",
        reply_markup=support_keyboard())


async def my_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    FIX v3: my_tickets correctly fetches from DB using get_user_tickets.
    Old v2 had import error — get_user_tickets was not imported in this handler.
    """
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
        "open":        "🔴 Open",
        "in_progress": "🟡 চলছে",
        "resolved":    "🟢 সমাধান",
        "closed":      "⚫ বন্ধ",
    }
    lines = ["🎫 *আমার সাপোর্ট টিকেট*\n"]
    for t in tickets:
        st = STATUS_MAP.get(t["status"], t["status"])
        lines.append(
            f"━━━━━━━━━━\n"
            f"🎫 Ticket #{t['ticket_id']} | {st}\n"
            f"📅 {str(t['created_at'])[:16]}\n"
            f"💬 {str(t['message'])[:80]}{'...' if len(str(t['message'])) > 80 else ''}\n"
        )
        if t.get("reply"):
            lines.append(f"📩 *উত্তর:* {str(t['reply'])[:120]}\n")

    await safe_edit(query, "\n".join(lines),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🆕 নতুন টিকেট", callback_data="new_ticket")],
            [InlineKeyboardButton("🏠 মেইন মেনু",  callback_data="main_menu")],
        ]))


async def noop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await safe_answer(update.callback_query)
