"""
handlers/product_handler.py
============================
Product browsing: categories → product list → product detail.
Cart management: add, remove, update quantity, view.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.queries import (
    get_categories, get_products_by_category, count_products_by_category,
    get_product, get_featured_products, get_bestseller_products,
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

logger = logging.getLogger(__name__)
PRODUCTS_PER_PAGE = 8


async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all active categories."""
    query = update.callback_query
    await safe_answer(query)
    categories = get_categories()

    if not categories:
        await safe_edit(
            query,
            "😔 এই মুহূর্তে কোনো পণ্য নেই। শীঘ্রই আসছে!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")
            ]])
        )
        return

    await safe_edit(
        query,
        "🛍️ *Product Categories*\n\nকোন ক্যাটাগরি থেকে কিনতে চান?",
        reply_markup=categories_keyboard(categories)
    )


async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show products in a category with pagination."""
    query = update.callback_query
    await safe_answer(query)

    # Parse: cat_Fashion or cat_Fashion_p2
    data = query.data  # e.g. "cat_Fashion" or "cat_Fashion_p2"
    parts = data.split("_p")
    cat_part = parts[0][4:]   # remove "cat_"
    page = int(parts[1]) if len(parts) > 1 else 0

    category = cat_part
    products = get_products_by_category(category, page=page, per_page=PRODUCTS_PER_PAGE)
    total = count_products_by_category(category)

    if not products:
        await safe_edit(
            query,
            f"😔 *{category}* ক্যাটাগরিতে এই মুহূর্তে কোনো পণ্য নেই।",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Categories", callback_data="browse_products")
            ]])
        )
        return

    await safe_edit(
        query,
        f"🛍️ *{category}* ({total} পণ্য)\n\nপণ্য বেছে নিন:",
        reply_markup=product_list_keyboard(products, category, page, total, PRODUCTS_PER_PAGE)
    )


async def show_product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show full product detail card."""
    query = update.callback_query
    await safe_answer(query)

    product_id = int(query.data.split("_")[1])
    await _show_product(update, context, product_id)


async def _show_product(update: Update, context: ContextTypes.DEFAULT_TYPE, product_id: int):
    """Internal helper to render a product detail (reused by wishlist toggle etc)."""
    query = update.callback_query
    user_id = update.effective_user.id

    product = get_product(product_id)
    if not product:
        await query.answer("❌ পণ্যটি পাওয়া যায়নি!", show_alert=True)
        return

    # Log recently viewed
    add_recently_viewed(user_id, product_id)

    in_stock = product["stock"] > 0
    in_wl    = is_in_wishlist(user_id, product_id)

    detail_text = format_product_card(product)
    keyboard = product_detail_keyboard(product_id, product["category"], user_id, in_stock, in_wl)

    # Try sending with image
    if product["image_url"]:
        try:
            await query.message.reply_photo(
                photo=product["image_url"],
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
            logger.warning(f"Could not send product image for #{product_id}: {e}")

    await safe_edit(query, detail_text, reply_markup=keyboard)


async def show_featured_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show featured products."""
    query = update.callback_query
    await safe_answer(query)
    products = get_featured_products(limit=8)

    if not products:
        await safe_edit(
            query,
            "🌟 এই মুহূর্তে কোনো Featured পণ্য নেই।",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🛍️ Browse All", callback_data="browse_products")
            ]])
        )
        return

    await safe_edit(
        query,
        "🌟 *Featured Products*\n\nআমাদের বিশেষভাবে বাছাই করা পণ্য:",
        reply_markup=featured_products_keyboard(products)
    )


async def show_bestsellers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show bestseller products."""
    query = update.callback_query
    await safe_answer(query)
    products = get_bestseller_products(limit=8)

    if not products:
        await safe_edit(
            query,
            "🔥 এই মুহূর্তে কোনো Bestseller পণ্য নেই।",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🛍️ Browse All", callback_data="browse_products")
            ]])
        )
        return

    await safe_edit(
        query,
        "🔥 *Bestseller Products*\n\nসবচেয়ে বেশি বিক্রিত পণ্য:",
        reply_markup=featured_products_keyboard(products)
    )


# ═══════════════════════════════════════════════════════════════════
# CART HANDLERS
# ═══════════════════════════════════════════════════════════════════

async def add_to_cart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add product to cart."""
    query = update.callback_query
    user_id = update.effective_user.id
    product_id = int(query.data.split("_")[1])

    product = get_product(product_id)
    if not product or product["stock"] <= 0:
        await query.answer("❌ পণ্যটি স্টকে নেই!", show_alert=True)
        return

    add_to_cart(user_id, product_id, quantity=1)
    await query.answer(f"✅ '{product['name'][:20]}' কার্টে যোগ হয়েছে!", show_alert=False)


async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's cart."""
    query = update.callback_query
    await safe_answer(query)
    user_id = update.effective_user.id
    items = get_cart_items(user_id)

    text = format_cart_summary(items)
    keyboard = cart_keyboard(items) if items else empty_cart_keyboard()
    await safe_edit(query, text, reply_markup=keyboard)


async def cart_quantity_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle ➕/➖ buttons in cart."""
    query = update.callback_query
    await safe_answer(query)
    user_id = update.effective_user.id

    # cartqty_<product_id>_inc or cartqty_<product_id>_dec
    parts = query.data.split("_")
    product_id = int(parts[1])
    action = parts[2]

    items = get_cart_items(user_id)
    current_qty = next((i["quantity"] for i in items if i["product_id"] == product_id), 1)
    product = get_product(product_id)

    if action == "inc":
        if current_qty >= min(10, product["stock"]):
            await query.answer("⚠️ সর্বোচ্চ পরিমাণে পৌঁছে গেছেন!", show_alert=False)
            return
        update_cart_quantity(user_id, product_id, current_qty + 1)
    else:
        if current_qty <= 1:
            remove_from_cart(user_id, product_id)
        else:
            update_cart_quantity(user_id, product_id, current_qty - 1)

    # Refresh cart view
    items = get_cart_items(user_id)
    text = format_cart_summary(items)
    keyboard = cart_keyboard(items) if items else empty_cart_keyboard()
    await safe_edit(query, text, reply_markup=keyboard)


async def cart_delete_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove item from cart."""
    query = update.callback_query
    await safe_answer(query)
    user_id = update.effective_user.id
    product_id = int(query.data.split("_")[1])

    remove_from_cart(user_id, product_id)

    items = get_cart_items(user_id)
    text = format_cart_summary(items)
    keyboard = cart_keyboard(items) if items else empty_cart_keyboard()
    await safe_edit(query, text, reply_markup=keyboard)


async def clear_cart_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear entire cart."""
    query = update.callback_query
    await safe_answer(query)
    user_id = update.effective_user.id
    clear_cart(user_id)
    await safe_edit(
        query,
        "🗑️ *Cart Cleared*\n\nআপনার কার্ট খালি করা হয়েছে।",
        reply_markup=empty_cart_keyboard()
    )


async def share_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Share product link."""
    query = update.callback_query
    product_id = int(query.data.split("_")[1])
    from config.settings import BOT_USERNAME
    link = f"https://t.me/{BOT_USERNAME}?start=product_{product_id}"
    await query.answer(f"🔗 Share: {link}", show_alert=True)
