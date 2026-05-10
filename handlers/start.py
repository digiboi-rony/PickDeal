"""handlers/start.py — /start command and main menu"""
import logging
from telegram import Update
from telegram.ext import ContextTypes

import models.user as user_model
import models.product as product_model
from keyboards.main_menu import main_menu
from utils.formatters import taka
from config.settings import BOT_NAME, BOT_TAGLINE
from middlewares.auth import is_rate_limited

logger = logging.getLogger(__name__)

WELCOME = """
🛍️ *{bot_name} তে স্বাগতম, {first_name}!*
_{tagline}_

━━━━━━━━━━━━━━━━━━━━
✨ *আজকের ফিচার্ড পণ্য:*
{featured_list}
━━━━━━━━━━━━━━━━━━━━

👇 নিচের মেনু থেকে শুরু করুন:
""".strip()


def _featured_list() -> str:
    products = product_model.get_featured()[:3]
    if not products:
        return "  _কোনো ফিচার্ড পণ্য নেই_"
    lines = []
    for p in products:
        eff = p["discount_price"] if p["discount_price"] else p["price"]
        lines.append(f"  • {p['name']} — *{taka(eff)}*")
    return "\n".join(lines)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if is_rate_limited(user.id):
        return

    # Register/update user
    user_model.upsert(user.id, user.username, user.first_name, user.last_name or "")

    # Handle referral link: /start ref_XXXX
    if context.args:
        payload = context.args[0]
        if payload.startswith("ref_"):
            context.user_data["referral_code"] = payload[4:]

    text = WELCOME.format(
        bot_name     = BOT_NAME,
        first_name   = user.first_name or "বন্ধু",
        tagline      = BOT_TAGLINE,
        featured_list= _featured_list(),
    )

    await update.message.reply_text(
        text,
        parse_mode   = "Markdown",
        reply_markup = main_menu(user.id),
    )


async def main_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return to main menu (callback: main_menu)."""
    query = update.callback_query
    await query.answer()
    user  = update.effective_user

    text = WELCOME.format(
        bot_name     = BOT_NAME,
        first_name   = user.first_name or "বন্ধু",
        tagline      = BOT_TAGLINE,
        featured_list= _featured_list(),
    )
    await query.edit_message_text(
        text,
        parse_mode   = "Markdown",
        reply_markup = main_menu(user.id),
    )
