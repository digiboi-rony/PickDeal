"""
handlers/start_handler.py
=========================
/start command, main menu, user profile, search, wishlist, recently viewed.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database.queries import (
    upsert_user, get_user, get_wishlist, get_recently_viewed,
    add_to_wishlist, remove_from_wishlist, is_in_wishlist, search_products,
    get_user_orders,
)
from keyboards.builder import (
    main_menu_keyboard, profile_keyboard, wishlist_keyboard,
    support_keyboard, back_to_menu,
)
from utils.helpers import safe_edit, safe_answer, ban_check
from utils.formatters import format_profile, format_product_card, format_price
from config.settings import BOT_NAME

logger = logging.getLogger(__name__)

SEARCH_STATE = 99


def _welcome_text(first_name: str) -> str:
    return (
        f"🎉 *আসসালামু আলাইকুম, {first_name}!*\n\n"
        f"*{BOT_NAME}* — বাংলাদেশের সেরা অনলাইন শপিং প্ল্যাটফর্মে স্বাগতম! 🇧🇩\n\n"
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
    """/start command — register user, show welcome message."""
    user = update.effective_user
    upsert_user(
        user_id=user.id,
        username=user.username or "",
        first_name=user.first_name or "",
        last_name=user.last_name or "",
    )
    logger.info(f"User {user.id} ({user.first_name}) started the bot.")

    # Handle referral payload: /start ref_ABCDEFGH
    if context.args:
        payload = context.args[0]
        if payload.startswith("ref_"):
            context.user_data["referral_code"] = payload[4:]

    await update.message.reply_text(
        _welcome_text(user.first_name or "বন্ধু"),
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to main menu from a callback."""
    query = update.callback_query
    await safe_answer(query)
    user = update.effective_user
    await safe_edit(
        query,
        _welcome_text(user.first_name or "বন্ধু"),
        reply_markup=main_menu_keyboard(),
    )


# ─── Profile ─────────────────────────────────────────────────────────────────

async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    user_id = update.effective_user.id
    user = get_user(user_id)
    orders = get_user_orders(user_id, limit=5)

    text = format_profile(user, orders)
    await safe_edit(query, text, reply_markup=profile_keyboard())


# ─── Wishlist ─────────────────────────────────────────────────────────────────

async def my_wishlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    user_id = update.effective_user.id
    products = get_wishlist(user_id)

    if not products:
        await safe_edit(
            query,
            "❤️ *My Wishlist*\n\nআপনার Wishlist খালি!\n\nপছন্দের পণ্যে ❤️ বাটন চাপুন।",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍️ Browse Products", callback_data="browse_products")],
                [InlineKeyboardButton("🏠 Main Menu",       callback_data="main_menu")],
            ])
        )
        return

    text = f"❤️ *My Wishlist* ({len(products)} items)\n\nআপনার পছন্দের পণ্যগুলি:"
    await safe_edit(query, text, reply_markup=wishlist_keyboard(products))


async def toggle_wishlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add or remove product from wishlist."""
    query = update.callback_query
    await safe_answer(query)
    user_id = update.effective_user.id
    product_id = int(query.data.split("_")[1])

    if is_in_wishlist(user_id, product_id):
        remove_from_wishlist(user_id, product_id)
        await query.answer("💔 Wishlist থেকে সরানো হয়েছে", show_alert=False)
    else:
        add_to_wishlist(user_id, product_id)
        await query.answer("❤️ Wishlist-এ যোগ হয়েছে!", show_alert=False)

    # Re-show product detail
    from handlers.product_handler import _show_product
    await _show_product(update, context, product_id)


# ─── Recently Viewed ──────────────────────────────────────────────────────────

async def recently_viewed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    user_id = update.effective_user.id
    products = get_recently_viewed(user_id, limit=8)

    if not products:
        await safe_edit(
            query,
            "🕐 *Recently Viewed*\n\nআপনি এখনো কোনো পণ্য দেখেননি।",
            reply_markup=back_to_menu()
        )
        return

    buttons = []
    for p in products:
        price = format_price(p["discount_price"] or p["price"])
        buttons.append([InlineKeyboardButton(
            f"🕐 {p['name'][:28]} | {price}",
            callback_data=f"product_{p['product_id']}"
        )])
    buttons.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])

    await safe_edit(
        query,
        f"🕐 *Recently Viewed* ({len(products)} items)",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


# ─── Search ───────────────────────────────────────────────────────────────────

async def search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show search prompt."""
    query = update.callback_query
    await safe_answer(query)
    await safe_edit(
        query,
        "🔎 *Product Search*\n\n"
        "পণ্যের নাম বা কীওয়ার্ড টাইপ করুন:\n"
        "_(উদাহরণ: shirt, watch, umbrella)_",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="main_menu")
        ]])
    )
    return SEARCH_STATE


async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Receive search query and show results."""
    q = update.message.text.strip()
    if not q:
        await update.message.reply_text("⚠️ Please enter a search keyword.")
        return SEARCH_STATE

    results = search_products(q, limit=10)

    if not results:
        await update.message.reply_text(
            f"😔 '*{q}*' - কোনো পণ্য পাওয়া যায়নি।\n\nঅন্য কীওয়ার্ড চেষ্টা করুন:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
            ]])
        )
        return ConversationHandler.END

    buttons = []
    for p in results:
        price = format_price(p["discount_price"] or p["price"])
        stock_icon = "✅" if p["stock"] > 0 else "❌"
        buttons.append([InlineKeyboardButton(
            f"{stock_icon} {p['name'][:28]} — {price}",
            callback_data=f"product_{p['product_id']}"
        )])
    buttons.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])

    await update.message.reply_text(
        f"🔎 *Search Results for '{q}'*\n{len(results)} পণ্য পাওয়া গেছে:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return ConversationHandler.END


# ─── Support ──────────────────────────────────────────────────────────────────

async def customer_support(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await safe_answer(query)
    await safe_edit(
        query,
        "💬 *Customer Support*\n\n"
        "আমরা সবসময় আপনার পাশে আছি! 🤝\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "📞 *Support Hours:* সকাল ৯টা — রাত ৯টা\n"
        "⏱️ *Response Time:* ১–৩ ঘণ্টার মধ্যে\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "নতুন সাপোর্ট টিকেট খুলুন অথবা আগের টিকেট দেখুন:",
        reply_markup=support_keyboard()
    )


async def noop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """No-operation callback for display-only buttons."""
    await safe_answer(update.callback_query)
