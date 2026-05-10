"""
utils/helpers.py — PickDeal BD v3
Decorators, validators, safe Telegram helpers, rate limiter.
BUG FIX: notify_admins now correctly accepts context, not update.
"""

import time
import logging
from functools import wraps
from telegram import Update
from telegram.ext import ContextTypes
from config.settings import ADMIN_IDS, RATE_LIMIT_SECONDS

logger = logging.getLogger(__name__)

# ── Rate limiter (in-memory, per user_id) ────────────────────────
_last_action: dict[int, float] = {}


# ════════════════════════════════════════════════
# DECORATORS
# ════════════════════════════════════════════════

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def admin_only(func):
    """Block non-admins from admin handlers."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        uid = update.effective_user.id
        if not is_admin(uid):
            if update.callback_query:
                await update.callback_query.answer("❌ Admin access only!", show_alert=True)
            elif update.message:
                await update.message.reply_text("❌ Unauthorized.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


def ban_check(func):
    """Block banned users."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        from database.queries import get_user
        uid = update.effective_user.id
        user = get_user(uid)
        if user and user["is_banned"]:
            if update.message:
                await update.message.reply_text("⛔ আপনি এই বট থেকে বাদ দেওয়া হয়েছেন।")
            elif update.callback_query:
                await update.callback_query.answer("⛔ আপনি banned.", show_alert=True)
            return
        return await func(update, context, *args, **kwargs)
    return wrapper


def rate_limit(func):
    """Simple per-user rate limiter."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        uid = update.effective_user.id
        now = time.time()
        if now - _last_action.get(uid, 0) < RATE_LIMIT_SECONDS:
            if update.callback_query:
                await update.callback_query.answer("⏳ একটু অপেক্ষা করুন...", show_alert=False)
            return
        _last_action[uid] = now
        return await func(update, context, *args, **kwargs)
    return wrapper


# ════════════════════════════════════════════════
# VALIDATORS
# ════════════════════════════════════════════════

def validate_bd_phone(phone: str) -> bool:
    p = phone.strip().replace(" ", "").replace("-", "")
    return p.startswith("01") and len(p) == 11 and p.isdigit()


def validate_name(name: str) -> tuple[bool, str]:
    n = name.strip()
    if len(n) < 3:
        return False, "⚠️ নাম কমপক্ষে ৩ অক্ষর হতে হবে। পুনরায় লিখুন:"
    if len(n) > 60:
        return False, "⚠️ নাম ৬০ অক্ষরের বেশি হওয়া যাবে না। পুনরায় লিখুন:"
    return True, n


def validate_address(address: str) -> tuple[bool, str]:
    a = address.strip()
    if len(a) < 10:
        return False, "⚠️ ঠিকানা খুব ছোট। বাড়ি নং, রোড, এলাকা, জেলা সহ লিখুন:"
    return True, a


def calculate_discount(subtotal: float, coupon) -> float:
    """Returns discount amount."""
    if not coupon:
        return 0.0
    if coupon["discount_type"] == "percent":
        return round(subtotal * coupon["discount_val"] / 100, 2)
    return round(min(float(coupon["discount_val"]), subtotal), 2)


# ════════════════════════════════════════════════
# SAFE TELEGRAM HELPERS
# ════════════════════════════════════════════════

async def safe_edit(query, text: str, parse_mode: str = "Markdown", **kwargs):
    """Edit message text silently if unchanged."""
    try:
        await query.edit_message_text(text, parse_mode=parse_mode, **kwargs)
    except Exception as e:
        if "Message is not modified" not in str(e):
            logger.warning(f"safe_edit: {e}")


async def safe_edit_caption(query, caption: str, parse_mode: str = "Markdown", **kwargs):
    """Edit message caption (for photo messages)."""
    try:
        await query.edit_message_caption(caption=caption, parse_mode=parse_mode, **kwargs)
    except Exception as e:
        if "Message is not modified" not in str(e):
            logger.warning(f"safe_edit_caption: {e}")


async def safe_answer(query, text: str = "", show_alert: bool = False):
    try:
        await query.answer(text, show_alert=show_alert)
    except Exception:
        pass


async def notify_admins(context: ContextTypes.DEFAULT_TYPE, text: str, **kwargs):
    """
    BUG FIX v3: Correctly uses context.bot to send messages.
    Old v2 passed `update` as first arg which caused AttributeError.
    """
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_message(chat_id=admin_id, text=text, **kwargs)
        except Exception as e:
            logger.error(f"notify_admins → {admin_id}: {e}")


async def notify_user(context: ContextTypes.DEFAULT_TYPE, user_id: int,
                      text: str, **kwargs) -> bool:
    try:
        await context.bot.send_message(chat_id=user_id, text=text, **kwargs)
        return True
    except Exception as e:
        logger.warning(f"notify_user {user_id}: {e}")
        return False


async def notify_admins_photo(context: ContextTypes.DEFAULT_TYPE,
                               photo, caption: str, **kwargs):
    """Send photo to all admins."""
    for admin_id in ADMIN_IDS:
        try:
            await context.bot.send_photo(
                chat_id=admin_id, photo=photo, caption=caption, **kwargs
            )
        except Exception as e:
            logger.error(f"notify_admins_photo → {admin_id}: {e}")
