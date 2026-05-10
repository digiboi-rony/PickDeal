"""handlers/products.py — browse, search, featured, product detail"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

import models.product as pm
import models.cart as cart_model
from keyboards.product_kb import (
    categories_kb, products_list_kb, product_detail_kb, search_results_kb
)
from keyboards.main_menu import main_menu, back_to_menu
from utils.formatters import product_card, taka
from middlewares.auth import is_rate_limited

logger = logging.getLogger(__name__)

# ConversationHandler state
SEARCHING = 50


async def browse(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show product categories."""
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🛍️ *ক্যাটাগরি বেছে নিন:*\n\nকোন ধরনের পণ্য দেখতে চান?",
        parse_mode   = "Markdown",
        reply_markup = categories_kb(),
    )


async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show products in a category. Pattern: cat_<id> or cat_<id>_p<page>"""
    query = update.callback_query
    await query.answer()

    parts  = query.data.split("_")   # ['cat', '2'] or ['cat', '2', 'p1']
    cat_id = int(parts[1])
    page   = int(parts[2][1:]) if len(parts) > 2 else 0

    cat = pm.get_conn() if False else None
    # Get category info
    cats = {c["cat_id"]: c for c in pm.get_categories()}
    cat  = cats.get(cat_id)
    if not cat:
        await query.answer("ক্যাটাগরি পাওয়া যায়নি!", show_alert=True)
        return

    count = pm.count_by_category(cat_id)
    if count == 0:
        await query.edit_message_text(
            f"{cat['emoji']} *{cat['name']}*\n\nএই ক্যাটাগরিতে এখনো কোনো পণ্য নেই।",
            parse_mode   = "Markdown",
            reply_markup = InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ ক্যাটাগরি", callback_data="browse")
            ]])
        )
        return

    await query.edit_message_text(
        f"{cat['emoji']} *{cat['name']}*\n\n{cat['description'] or ''}\n\n"
        f"📦 মোট পণ্য: {count}টি\n\nপণ্য বেছে নিন:",
        parse_mode   = "Markdown",
        reply_markup = products_list_kb(cat_id, page),
    )


async def show_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show product detail. Pattern: product_<id>"""
    query = update.callback_query
    await query.answer()

    product_id = int(query.data.split("_")[1])
    p = pm.get(product_id)
    if not p:
        await query.answer("পণ্যটি পাওয়া যায়নি!", show_alert=True)
        return

    # Check wishlist
    user_id   = update.effective_user.id
    in_wish   = _in_wishlist(user_id, product_id)
    images    = pm.get_images(product_id)
    text      = product_card(p)

    kb = product_detail_kb(product_id, in_wish)

    if images:
        try:
            await query.message.reply_photo(
                photo        = images[0]["file_id"],
                caption      = text,
                parse_mode   = "Markdown",
                reply_markup = kb,
            )
            await query.message.delete()
            return
        except Exception as e:
            logger.warning(f"Could not send product image: {e}")

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)


async def add_to_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add product to cart. Pattern: addcart_<product_id>"""
    query = update.callback_query
    user_id    = update.effective_user.id
    product_id = int(query.data.split("_")[1])

    p = pm.get(product_id)
    if not p or p["stock"] <= 0:
        await query.answer("❌ পণ্যটি স্টকে নেই!", show_alert=True)
        return

    cart_model.add_item(user_id, product_id, 1)
    count = cart_model.count_items(user_id)
    await query.answer(f"✅ কার্টে যোগ হয়েছে! মোট: {count}টি পণ্য", show_alert=False)


async def buy_now(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Buy Now = add to cart then go to cart. Pattern: buynow_<product_id>"""
    query = update.callback_query
    user_id    = update.effective_user.id
    product_id = int(query.data.split("_")[1])

    p = pm.get(product_id)
    if not p or p["stock"] <= 0:
        await query.answer("❌ পণ্যটি স্টকে নেই!", show_alert=True)
        return

    cart_model.add_item(user_id, product_id, 1)
    # Redirect to cart
    query.data = "view_cart"
    from handlers.cart import view_cart
    await view_cart(update, context)


async def toggle_wishlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle wishlist. Pattern: wish_<product_id>"""
    query = update.callback_query
    await query.answer()
    user_id    = update.effective_user.id
    product_id = int(query.data.split("_")[1])

    from database.connection import get_conn
    conn = get_conn()
    existing = conn.execute(
        "SELECT wish_id FROM wishlist WHERE user_id=? AND product_id=?",
        (user_id, product_id)
    ).fetchone()

    if existing:
        conn.execute(
            "DELETE FROM wishlist WHERE user_id=? AND product_id=?", (user_id, product_id)
        )
        conn.commit()
        await query.answer("💔 উইশলিস্ট থেকে সরানো হয়েছে।")
    else:
        conn.execute(
            "INSERT OR IGNORE INTO wishlist(user_id,product_id) VALUES(?,?)",
            (user_id, product_id)
        )
        conn.commit()
        await query.answer("❤️ উইশলিস্টে যোগ হয়েছে!")

    # Refresh product detail
    p        = pm.get(product_id)
    in_wish  = not bool(existing)
    text     = product_card(p)
    kb       = product_detail_kb(product_id, in_wish)
    try:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    except Exception:
        pass


async def show_featured(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show featured products."""
    query = update.callback_query
    await query.answer()

    products = pm.get_featured()
    if not products:
        await query.edit_message_text(
            "⭐ এখন কোনো ফিচার্ড পণ্য নেই।",
            reply_markup=back_to_menu()
        )
        return

    buttons = [
        [InlineKeyboardButton(
            f"⭐ {p['name']} — {taka(p['discount_price'] or p['price'])}",
            callback_data=f"product_{p['product_id']}"
        )]
        for p in products
    ]
    buttons.append([InlineKeyboardButton("⬅️ মেনু", callback_data="main_menu")])

    await query.edit_message_text(
        "⭐ *ফিচার্ড পণ্য সমূহ:*\n\nআমাদের বিশেষ পণ্য সিলেকশন:",
        parse_mode   = "Markdown",
        reply_markup = InlineKeyboardMarkup(buttons),
    )


# ─── Search ConversationHandler ──────────────────────────────────────────────
async def search_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask user to type a search query."""
    query = update.callback_query
    await query.answer()
    context.user_data["state"] = "searching"
    await query.edit_message_text(
        "🔍 *পণ্য সার্চ করুন*\n\nপণ্যের নাম বা কীওয়ার্ড লিখুন:\n_(যেমন: watch, umbrella, shirt)_",
        parse_mode   = "Markdown",
        reply_markup = InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ বাতিল", callback_data="main_menu")
        ]])
    )
    return SEARCHING


async def do_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Perform product search."""
    query_text = update.message.text.strip()
    if len(query_text) < 2:
        await update.message.reply_text("⚠️ কমপক্ষে ২টি অক্ষর লিখুন।")
        return SEARCHING

    results = pm.search(query_text)
    if not results:
        await update.message.reply_text(
            f"😔 *'{query_text}'* দিয়ে কোনো পণ্য পাওয়া যায়নি।\n\nঅন্য কীওয়ার্ড ট্রাই করুন।",
            parse_mode   = "Markdown",
            reply_markup = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔍 আবার সার্চ", callback_data="search_prompt"),
                InlineKeyboardButton("⬅️ মেনু",       callback_data="main_menu"),
            ]])
        )
        return ConversationHandler.END

    await update.message.reply_text(
        f"🔍 *'{query_text}'* — {len(results)}টি পণ্য পাওয়া গেছে:",
        parse_mode   = "Markdown",
        reply_markup = search_results_kb(results, query_text),
    )
    return ConversationHandler.END


def _in_wishlist(user_id: int, product_id: int) -> bool:
    from database.connection import get_conn
    row = get_conn().execute(
        "SELECT 1 FROM wishlist WHERE user_id=? AND product_id=?", (user_id, product_id)
    ).fetchone()
    return bool(row)
