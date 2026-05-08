"""
handlers/product_handler.py
============================
Handles product browsing: categories → product list → product detail.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from database.queries import get_categories, get_products_by_category, get_product
from utils.helpers import format_price, get_category_emoji, format_product_card

logger = logging.getLogger(__name__)

# State constant (used in ConversationHandler if needed)
BROWSING = 10


async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show all product categories as inline buttons.
    Triggered when user taps 'Browse Products'.
    """
    query = update.callback_query
    await query.answer()

    categories = get_categories()

    if not categories:
        await query.edit_message_text(
            "😔 No products available right now. Check back soon!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Back", callback_data="main_menu")
            ]])
        )
        return

    # Build one button per category
    buttons = []
    for cat in categories:
        emoji = get_category_emoji(cat)
        buttons.append([InlineKeyboardButton(f"{emoji} {cat}", callback_data=f"cat_{cat}")])

    buttons.append([InlineKeyboardButton("⬅️ Back to Menu", callback_data="main_menu")])

    await query.edit_message_text(
        "🛍️ *Choose a Category*\n\nWhat are you looking for today?",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def show_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show all products in a selected category.
    Triggered by 'cat_<category_name>' callback.
    """
    query = update.callback_query
    await query.answer()

    # Extract category name from callback data (e.g., "cat_Electronics" → "Electronics")
    category = query.data[4:]
    products = get_products_by_category(category)

    if not products:
        await query.edit_message_text(
            f"😔 No products in *{category}* right now.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Back", callback_data="browse_products")
            ]])
        )
        return

    emoji = get_category_emoji(category)
    buttons = []
    for p in products:
        stock_icon = "✅" if p["stock"] > 0 else "❌"
        label = f"{stock_icon} {p['name']} — {format_price(p['price'])}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"product_{p['product_id']}")])

    buttons.append([InlineKeyboardButton("⬅️ Back to Categories", callback_data="browse_products")])

    await query.edit_message_text(
        f"{emoji} *{category}* Products\n\nTap a product to see details:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def show_product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show full details for a single product.
    Triggered by 'product_<product_id>' callback.
    """
    query = update.callback_query
    await query.answer()

    # Extract product ID from callback data
    product_id = int(query.data.split("_")[1])
    product = get_product(product_id)

    if not product:
        await query.answer("❌ Product not found!", show_alert=True)
        return

    # Save product_id in user session for the order flow
    context.user_data["selected_product_id"] = product_id

    detail_text = format_product_card(product)

    # Build action buttons
    if product["stock"] > 0:
        action_buttons = [
            [InlineKeyboardButton("🛒 Order Now!", callback_data=f"order_{product_id}")]
        ]
    else:
        action_buttons = [
            [InlineKeyboardButton("❌ Out of Stock", callback_data="noop")]
        ]

    action_buttons.append([
        InlineKeyboardButton(f"⬅️ Back", callback_data=f"cat_{product['category']}")
    ])

    # Try to send product image if available
    if product["image_url"]:
        try:
            await query.message.reply_photo(
                photo=product["image_url"],
                caption=detail_text,
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(action_buttons),
            )
            await query.message.delete()
            return
        except Exception as e:
            logger.warning(f"Could not send product image: {e}")

    # Fallback: text-only product detail
    await query.edit_message_text(
        detail_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(action_buttons),
    )
