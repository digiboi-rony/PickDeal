"""keyboards/main_menu.py"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import models.cart as cart_model


def main_menu(user_id=None) -> InlineKeyboardMarkup:
    cart_count = cart_model.count_items(user_id) if user_id else 0
    cart_label = f"🛒 কার্ট ({cart_count})" if cart_count > 0 else "🛒 কার্ট"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛍️ পণ্য ব্রাউজ করুন",  callback_data="browse")],
        [InlineKeyboardButton("🔍 পণ্য সার্চ করুন",   callback_data="search_prompt"),
         InlineKeyboardButton("⭐ ফিচার্ড",            callback_data="featured")],
        [InlineKeyboardButton(cart_label,               callback_data="view_cart"),
         InlineKeyboardButton("📋 আমার অর্ডার",        callback_data="my_orders")],
        [InlineKeyboardButton("👤 প্রোফাইল",            callback_data="profile"),
         InlineKeyboardButton("💬 সাপোর্ট",            callback_data="support")],
    ])


def back_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("⬅️ মেনুতে ফিরুন", callback_data="main_menu")
    ]])
