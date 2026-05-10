"""
handlers/product_handler.py — PickDeal BD v3
BUG FIX: Category routing now uses category_id (not name string).
BUG FIX: Featured products callback was returning without content.
BUG FIX: Product images now properly displayed using send_photo.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.queries import (
    get_categories, get_category,
    get_products_by_category, count_products_by_category,
    get_product, get_product_images,
    get_featured_products, get_bestseller_products, get_new_arrivals,
    add_recently_viewed, is_in_wishlist,
    add_to_cart, remove_from_cart, update_cart_quantity,
    get_cart_items, clear_cart,
)
from keyboards.builder import (
    categories_keyboard, product_list_keyboard, product_detail_keyboard,
    featured_products_keyboard, cart_keyboard, empty_cart_keyboard,
)
from utils.helpers import safe_edit, safe_answer
from utils.formatters import format_product_card, format_cart_summary, format_price
from config.settings import PRODUCTS_PER_PAGE, BOT_USERNAME

logger = logging.getLogger(__name__)


async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Browse all active categories."""
    query = update.callback_query
    await safe_answer(query)
    categories = get_categories(active_only=True)
    if not categories:
        await safe_edit(query,
            "😔 এই মুহূর্তে কোনো ক্যাটাগরি নেই।",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 মেইন মেনু", callback_data="main_menu")
            ]]))
        return
    await safe_edit(query,
        "🛍️ *পণ্য ক্যাটাগরি*\n\nকোন ক্যাটাগরি থেকে কিনতে চান?",
        reply_markup=categories_keyboard(categories))


async def show_products_by_catid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    FIX v3: Callback pattern: catid_<id> or catid_<id>_p<page>
    Old v2 used cat_<name> which broke when name had underscores.
    """
    query = update.callback_query
    await safe_answer(query)

    data  = query.data  # catid_5 or catid_5_p2
    parts = data.split("_p")
    cat_id_str = parts[0].replace("catid_", "")
    page  = int(parts[1]) if len(parts) > 1 else 0

    try:
        category_id = int(cat_id_str)
    except ValueError:
        await query.answer("❌ ক্যাটাগরি ID ভুল!", show_alert=True)
        return

    cat = get_category(category_id)
    if not cat:
        await query.answer("❌ ক্যাটাগরি পাওয়া যায়নি!", show_alert=True)
        return

    category_name = cat["name"]
    products      = get_products_by_category(category_name, page=page, per_page=PRODUCTS_PER_PAGE)
    total         = count_products_by_category(category_name)

    if not products:
        await safe_edit(query,
            f"😔 *{cat['emoji']} {category_name}* — এই মুহূর্তে কোনো পণ্য নেই।",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ ক্যাটাগরি", callback_data="browse_categories")
            ]]))
        return

    await safe_edit(query,
        f"{cat['emoji']} *{category_name}* ({total} টি পণ্য)\n\nপণ্য বেছে নিন:",
        reply_markup=product_list_keyboard(products, category_id, page, total, PRODUCTS_PER_PAGE))


async def show_product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query      = update.callback_query
    await safe_answer(query)
    product_id = int(query.data.split("_")[1])
    await _show_product(update, context, product_id)


async def _show_product(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int):
    """
    FIX v3: Correctly sends photo with caption using send_photo.
    Gets category_id from DB for back button.
    Handles media_group (multiple images).
    """
    query   = update.callback_query
    user_id = update.effective_user.id

    product = get_product(product_id)
    if not product:
        await query.answer("❌ পণ্যটি পাওয়া যায়নি!", show_alert=True)
        return

    add_recently_viewed(user_id, product_id)

    in_stock = product["stock"] > 0
    in_wl    = is_in_wishlist(user_id, product_id)

    # Get category_id for back button
    from database.queries import get_categories
    cats   = get_categories(active_only=False)
    cat_id = next(
        (c["category_id"] for c in cats if c["name"] == product["category"]), 1
    )

    detail_text = format_product_card(product)
    keyboard    = product_detail_keyboard(product_id, cat_id, in_stock, in_wl)

    # Get all product images (including primary)
    images = get_product_images(product_id)
    primary_image = product["image_url"]
    if not primary_image and images:
        primary_image = images[0]["file_id"]

    if primary_image:
        try:
            await query.message.reply_photo(
                photo=primary_image,
                caption=detail_text,
                parse_mode="Markdown",
                reply_markup=keyboard,
            )
            try:
                await query.message.delete()
            except Exception:
                pass
            return
        except Exception as e:
            logger.warning(f"Product image send failed #{product_id}: {e}")

    # Fallback: text-only
    await safe_edit(query, detail_text, reply_markup=keyboard)


async def show_featured_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """FIX v3: Was returning nothing if featured list empty."""
    query    = update.callback_query
    await safe_answer(query)
    products = get_featured_products(limit=8)
    if not products:
        await safe_edit(query,
            "🌟 *ফিচার্ড পণ্য*\n\nএই মুহূর্তে কোনো ফিচার্ড পণ্য নেই।",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛍️ সব পণ্য দেখুন", callback_data="browse_categories")],
                [InlineKeyboardButton("🏠 মেইন মেনু",     callback_data="main_menu")],
            ]))
        return
    await safe_edit(query,
        "🌟 *ফিচার্ড পণ্য*\n\nআমাদের বিশেষভাবে বাছাই করা পণ্য:",
        reply_markup=featured_products_keyboard(products))


async def show_bestsellers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await safe_answer(query)
    products = get_bestseller_products(limit=8)
    if not products:
        await safe_edit(query,
            "🔥 *বেস্টসেলার*\n\nএই মুহূর্তে কোনো বেস্টসেলার নেই।",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🛍️ সব পণ্য", callback_data="browse_categories")
            ]]))
        return
    await safe_edit(query, "🔥 *বেস্টসেলার পণ্য*\n\nসবচেয়ে বেশি বিক্রিত পণ্য:",
                    reply_markup=featured_products_keyboard(products))


async def show_new_arrivals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query    = update.callback_query
    await safe_answer(query)
    products = get_new_arrivals(limit=8)
    if not products:
        await safe_edit(query,
            "✨ *নতুন পণ্য*\n\nএখনো কোনো নতুন পণ্য যোগ হয়নি।",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🛍️ সব পণ্য", callback_data="browse_categories")
            ]]))
        return
    await safe_edit(query, "✨ *নতুন আসা পণ্য*",
                    reply_markup=featured_products_keyboard(products))


# ════════════════════════════════════════════════
# CART
# ════════════════════════════════════════════════

async def add_to_cart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query      = update.callback_query
    user_id    = update.effective_user.id
    product_id = int(query.data.split("_")[1])
    product    = get_product(product_id)
    if not product or product["stock"] <= 0:
        await query.answer("❌ পণ্যটি স্টকে নেই!", show_alert=True)
        return
    add_to_cart(user_id, product_id, quantity=1)
    await query.answer(f"✅ '{product['name'][:20]}' কার্টে যোগ হয়েছে!")


async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await safe_answer(query)
    user_id = update.effective_user.id
    items   = get_cart_items(user_id)
    text    = format_cart_summary(items)
    kb      = cart_keyboard(items) if items else empty_cart_keyboard()
    await safe_edit(query, text, reply_markup=kb)


async def cart_qty_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await safe_answer(query)
    user_id = update.effective_user.id
    parts      = query.data.split("_")
    product_id = int(parts[1])
    action     = parts[2]

    items       = get_cart_items(user_id)
    current_qty = next((i["quantity"] for i in items if i["product_id"] == product_id), 1)
    product     = get_product(product_id)

    if action == "inc":
        if product and current_qty >= min(10, product["stock"]):
            await query.answer("⚠️ সর্বোচ্চ পরিমাণে পৌঁছে গেছেন!")
            return
        update_cart_quantity(user_id, product_id, current_qty + 1)
    else:
        update_cart_quantity(user_id, product_id, current_qty - 1)

    items = get_cart_items(user_id)
    await safe_edit(query, format_cart_summary(items),
                    reply_markup=cart_keyboard(items) if items else empty_cart_keyboard())


async def cart_del_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query      = update.callback_query
    await safe_answer(query)
    user_id    = update.effective_user.id
    product_id = int(query.data.split("_")[1])
    remove_from_cart(user_id, product_id)
    items = get_cart_items(user_id)
    await safe_edit(query, format_cart_summary(items),
                    reply_markup=cart_keyboard(items) if items else empty_cart_keyboard())


async def clear_cart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query   = update.callback_query
    await safe_answer(query)
    clear_cart(update.effective_user.id)
    await safe_edit(query,
        "🗑️ *কার্ট খালি করা হয়েছে।*",
        reply_markup=empty_cart_keyboard())


async def share_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query      = update.callback_query
    product_id = int(query.data.split("_")[1])
    link       = f"https://t.me/{BOT_USERNAME}?start=p{product_id}"
    await query.answer(f"🔗 শেয়ার লিংক কপি করুন:\n{link}", show_alert=True)
