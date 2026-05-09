"""
utils/helpers.py
================
Shared helper functions, validators, and decorators.
"""

import logging
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from config.settings import ADMIN_IDS

logger = logging.getLogger(__name__)


# ─── Admin Check ─────────────────────────────────────────────────────────────

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def admin_only(func):
    """Decorator: restricts handler to admins only."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        if not is_admin(user_id):
            if update.callback_query:
                await update.callback_query.answer("❌ Admin access required!", show_alert=True)
            elif update.message:
                await update.message.reply_text("❌ You are not authorized to use this command.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


def ban_check(func):
    """Decorator: blocks banned users from using the bot."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        from database.queries import get_user
        user_id = update.effective_user.id
        user = get_user(user_id)
        if user and user["is_banned"]:
            if update.message:
                await update.message.reply_text("⛔ You have been banned from this bot.")
            elif update.callback_query:
                await update.callback_query.answer("⛔ You are banned.", show_alert=True)
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


# ─── Validation ──────────────────────────────────────────────────────────────

def validate_bd_phone(phone: str) -> bool:
    """Validate Bangladesh phone number (01XXXXXXXXX)."""
    phone = phone.strip().replace(" ", "").replace("-", "")
    return phone.startswith("01") and len(phone) == 11 and phone.isdigit()


def validate_name(name: str) -> tuple[bool, str]:
    name = name.strip()
    if len(name) < 3:
        return False, "⚠️ নাম অন্তত ৩ অক্ষরের হতে হবে। Please enter your full name:"
    if len(name) > 60:
        return False, "⚠️ নাম ৬০ অক্ষরের বেশি হওয়া যাবে না। Please shorten your name:"
    return True, name


def validate_address(address: str) -> tuple[bool, str]:
    address = address.strip()
    if len(address) < 10:
        return False, "⚠️ Address is too short. Please enter your full delivery address (House, Road, Area, District):"
    return True, address


def calculate_discount(price: float, coupon) -> tuple[float, float]:
    """Returns (discount_amount, final_price)."""
    if not coupon:
        return 0, price
    disc = 0
    if coupon["discount_pct"] > 0:
        disc = price * coupon["discount_pct"] / 100
    elif coupon["discount_flat"] > 0:
        disc = coupon["discount_flat"]
    disc = min(disc, price)
    return round(disc, 2), round(price - disc, 2)


# ─── Safe Telegram Helpers ───────────────────────────────────────────────────

async def safe_edit(query, text: str, parse_mode="Markdown", **kwargs):
    """Edit message text, silently ignore if message is unchanged."""
    try:
        await query.edit_message_text(text, parse_mode=parse_mode, **kwargs)
    except Exception as e:
        if "Message is not modified" not in str(e):
            logger.warning(f"safe_edit failed: {e}")


async def safe_answer(query, text: str = "", show_alert: bool = False):
    """Answer callback query, silently ignore errors."""
    try:
        await query.answer(text, show_alert=show_alert)
    except Exception:
        pass


async def notify_admins(context, text: str, **kwargs):
    """Send a message to all admins."""
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=text, **kwargs)
        except Exception as e:
            logger.error(f"notify_admins failed for {admin_id}: {e}")


async def notify_user(context, user_id: int, text: str, **kwargs):
    """Send a notification to a specific user."""
    try:
        await context.bot.send_message(chat_id=user_id, text=text, **kwargs)
        return True
    except Exception as e:
        logger.warning(f"notify_user {user_id} failed: {e}")
        return False
