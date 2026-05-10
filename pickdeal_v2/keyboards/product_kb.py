"""keyboards/product_kb.py"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import models.product as pm
from config.settings import PRODUCTS_PER_PAGE


def categories_kb() -> InlineKeyboardMarkup:
    cats = pm.get_categories()
    buttons = [
        [InlineKeyboardButton(f"{c['emoji']} {c['name']}", callback_data=f"cat_{c['cat_id']}")]
        for c in cats
    ]
    buttons.append([InlineKeyboardButton("⬅️ মেনু", callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)


def products_list_kb(cat_id, page=0) -> InlineKeyboardMarkup:
    products = pm.get_by_category(cat_id, page, PRODUCTS_PER_PAGE)
    total    = pm.count_by_category(cat_id)
    buttons  = []

    for p in products:
        eff   = p["discount_price"] if p["discount_price"] else p["price"]
        stock = "✅" if p["stock"] > 0 else "❌"
        label = f"{stock} {p['name']} — ৳{eff:,.0f}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"product_{p['product_id']}")])

    # Pagination
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ আগের", callback_data=f"cat_{cat_id}_p{page-1}"))
    total_pages = (total + PRODUCTS_PER_PAGE - 1) // PRODUCTS_PER_PAGE
    nav.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="noop"))
    if (page + 1) * PRODUCTS_PER_PAGE < total:
        nav.append(InlineKeyboardButton("পরের ➡️", callback_data=f"cat_{cat_id}_p{page+1}"))
    if nav:
        buttons.append(nav)

    buttons.append([InlineKeyboardButton("⬅️ ক্যাটাগরি", callback_data="browse")])
    return InlineKeyboardMarkup(buttons)


def product_detail_kb(product_id, in_wishlist=False) -> InlineKeyboardMarkup:
    wish_label = "💔 উইশলিস্ট থেকে সরান" if in_wishlist else "❤️ উইশলিস্টে যোগ করুন"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🛒 কার্টে যোগ করুন",  callback_data=f"addcart_{product_id}"),
         InlineKeyboardButton("⚡ এখনই কিনুন",       callback_data=f"buynow_{product_id}")],
        [InlineKeyboardButton(wish_label,             callback_data=f"wish_{product_id}")],
        [InlineKeyboardButton("⬅️ পিছনে",            callback_data="browse"),
         InlineKeyboardButton("🛒 কার্ট দেখুন",      callback_data="view_cart")],
    ])


def search_results_kb(results, query) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(f"🔹 {p['name']} — ৳{p['discount_price'] or p['price']:,.0f}",
                              callback_data=f"product_{p['product_id']}")]
        for p in results
    ]
    buttons.append([InlineKeyboardButton("🔍 আবার সার্চ", callback_data="search_prompt"),
                    InlineKeyboardButton("⬅️ মেনু",       callback_data="main_menu")])
    return InlineKeyboardMarkup(buttons)
