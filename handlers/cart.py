"""handlers/cart.py — cart view, quantity updates, checkout redirect"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import models.cart as cart_model
from keyboards.order_kb import cart_kb
from utils.formatters import cart_summary

logger = logging.getLogger(__name__)


async def view_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show cart contents."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    items = cart_model.get_items(user_id)
    text  = cart_summary(items)
    kb    = cart_kb(items) if items else InlineKeyboardMarkup([[
        InlineKeyboardButton("🛍️ পণ্য দেখুন", callback_data="browse"),
        InlineKeyboardButton("⬅️ মেনু",        callback_data="main_menu"),
    ]])
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)


async def qty_increase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pattern: qty_inc_<product_id>"""
    query = update.callback_query
    await query.answer()
    user_id    = update.effective_user.id
    product_id = int(query.data.split("_")[2])

    items = cart_model.get_items(user_id)
    cur   = next((it["quantity"] for it in items if it["product_id"] == product_id), 0)
    stock = next((it["stock"]    for it in items if it["product_id"] == product_id), 0)

    if cur >= stock:
        await query.answer(f"❌ স্টকে মাত্র {stock}টি আছে!", show_alert=True)
        return
    if cur >= 10:
        await query.answer("❌ সর্বোচ্চ ১০টি যোগ করা যাবে।", show_alert=True)
        return

    cart_model.update_qty(user_id, product_id, cur + 1)
    await _refresh_cart(query, user_id)


async def qty_decrease(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pattern: qty_dec_<product_id>"""
    query = update.callback_query
    await query.answer()
    user_id    = update.effective_user.id
    product_id = int(query.data.split("_")[2])

    items = cart_model.get_items(user_id)
    cur   = next((it["quantity"] for it in items if it["product_id"] == product_id), 1)
    cart_model.update_qty(user_id, product_id, cur - 1)
    await _refresh_cart(query, user_id)


async def remove_item(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pattern: remove_<product_id>"""
    query = update.callback_query
    await query.answer()
    user_id    = update.effective_user.id
    product_id = int(query.data.split("_")[1])

    cart_model.remove_item(user_id, product_id)
    await query.answer("🗑️ পণ্যটি সরানো হয়েছে।")
    await _refresh_cart(query, user_id)


async def clear_cart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear entire cart."""
    query = update.callback_query
    await query.answer()
    cart_model.clear(update.effective_user.id)
    await query.edit_message_text(
        "🛒 কার্ট খালি করা হয়েছে।",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("🛍️ পণ্য দেখুন", callback_data="browse"),
            InlineKeyboardButton("⬅️ মেনু",        callback_data="main_menu"),
        ]])
    )


async def _refresh_cart(query, user_id):
    """Refresh the cart message in place."""
    items = cart_model.get_items(user_id)
    text  = cart_summary(items)
    kb    = cart_kb(items) if items else InlineKeyboardMarkup([[
        InlineKeyboardButton("🛍️ পণ্য দেখুন", callback_data="browse"),
        InlineKeyboardButton("⬅️ মেনু",        callback_data="main_menu"),
    ]])
    try:
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)
    except Exception:
        pass
