"""handlers/profile.py — user profile, wishlist, referral"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import models.user as user_model
import models.order as order_model
import models.product as pm
from database.connection import get_conn
from utils.formatters import taka

logger = logging.getLogger(__name__)


async def profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user profile. Callback: profile"""
    query = update.callback_query
    await query.answer()
    u = update.effective_user
    row = user_model.get(u.id)

    orders  = order_model.get_user_orders(u.id)
    spent   = float(row["total_spent"]) if row else 0
    ref_code = row["ref_code"] if row else "—"

    text = (
        f"👤 *আমার প্রোফাইল*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"নাম: {u.first_name} {u.last_name or ''}\n"
        f"Username: @{u.username or '—'}\n"
        f"Telegram ID: `{u.id}`\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📦 মোট অর্ডার: {len(orders)}টি\n"
        f"💰 মোট খরচ: {taka(spent)}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔗 *রেফারেল কোড:* `{ref_code}`\n"
        f"বন্ধুকে ইনভাইট করুন:\n"
        f"`https://t.me/PickDealBD_bot?start=ref_{ref_code}`"
    )

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("❤️ উইশলিস্ট", callback_data="my_wishlist"),
             InlineKeyboardButton("📋 অর্ডার",    callback_data="my_orders")],
            [InlineKeyboardButton("⬅️ মেনু",      callback_data="main_menu")],
        ])
    )


async def wishlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user wishlist. Callback: my_wishlist"""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    rows = get_conn().execute("""
        SELECT p.product_id, p.name, p.discount_price, p.price
        FROM wishlist w JOIN products p ON w.product_id=p.product_id
        WHERE w.user_id=? ORDER BY w.added_at DESC
    """, (user_id,)).fetchall()

    if not rows:
        await query.edit_message_text(
            "❤️ *উইশলিস্ট খালি।*\n\nপণ্য দেখতে গিয়ে ❤️ চাপুন।",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🛍️ পণ্য দেখুন", callback_data="browse"),
                InlineKeyboardButton("⬅️ মেনু",        callback_data="main_menu"),
            ]])
        )
        return

    buttons = [
        [InlineKeyboardButton(
            f"❤️ {r['name']} — {taka(r['discount_price'] or r['price'])}",
            callback_data=f"product_{r['product_id']}"
        )]
        for r in rows
    ]
    buttons.append([InlineKeyboardButton("⬅️ প্রোফাইল", callback_data="profile")])

    await query.edit_message_text(
        f"❤️ *আমার উইশলিস্ট* ({len(rows)}টি পণ্য)",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )
