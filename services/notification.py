"""
services/notification.py
========================
Auto-notification service.
Sends Telegram messages to customers when order status changes.
"""
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from models.order import STATUS_EMOJI, STATUS_LABEL

logger = logging.getLogger(__name__)

# Customer-facing notification messages for each status
CUSTOMER_MESSAGES = {
    "payment_confirmed": (
        "✅ *পেমেন্ট নিশ্চিত হয়েছে!*\n\n"
        "আপনার অর্ডার #{order_id} এর পেমেন্ট ভেরিফাই হয়েছে।\n"
        "আমরা এখন আপনার পণ্য প্রস্তুত করছি। 🎉"
    ),
    "processing": (
        "⚙️ *অর্ডার প্রসেস হচ্ছে!*\n\n"
        "অর্ডার #{order_id} প্যাক করার প্রস্তুতি চলছে।"
    ),
    "packed": (
        "📦 *অর্ডার প্যাক হয়েছে!*\n\n"
        "অর্ডার #{order_id} প্যাক সম্পন্ন।\n"
        "শীঘ্রই শিপমেন্ট শুরু হবে।"
    ),
    "shipping": (
        "🚚 *অর্ডার শিপমেন্ট শুরু হয়েছে!*\n\n"
        "অর্ডার #{order_id} কুরিয়ারে পাঠানো হয়েছে।\n"
        "ডেলিভারি: ১-৩ কার্যদিবস।"
    ),
    "out_for_delivery": (
        "🛵 *ডেলিভারি চলছে!*\n\n"
        "অর্ডার #{order_id} এখন ডেলিভারিতে আছে।\n"
        "আজকেই পাবেন! ফোন রেডি রাখুন। 📞"
    ),
    "delivered": (
        "🎉 *ডেলিভারি সম্পন্ন!*\n\n"
        "অর্ডার #{order_id} পৌঁছে গেছে।\n\n"
        "PickDeal BD তে শপিং করার জন্য ধন্যবাদ! 🛍️\n"
        "আপনার অভিজ্ঞতা কেমন ছিল?"
    ),
    "cancelled": (
        "❌ *অর্ডার বাতিল হয়েছে।*\n\n"
        "অর্ডার #{order_id} বাতিল করা হয়েছে।\n"
        "পেমেন্ট করা থাকলে ২-৩ কার্যদিবসে রিফান্ড হবে।\n"
        "সাহায্যের জন্য সাপোর্টে যোগাযোগ করুন।"
    ),
}


async def notify_customer(bot, user_id: int, order_id: int, new_status: str):
    """Send status update notification to customer."""
    template = CUSTOMER_MESSAGES.get(new_status)
    if not template:
        return

    text = template.format(order_id=order_id)
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("📋 অর্ডার দেখুন", callback_data=f"order_detail_{order_id}")
    ]])

    try:
        await bot.send_message(
            chat_id=user_id,
            text=text,
            parse_mode="Markdown",
            reply_markup=kb,
        )
        logger.info(f"✅ Notified user {user_id} → order #{order_id} → {new_status}")
    except Exception as e:
        logger.error(f"❌ Failed to notify user {user_id}: {e}")


async def notify_admins(bot, admin_ids: list[int], text: str, kb=None):
    """Broadcast a message to all admins."""
    for admin_id in admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=text,
                parse_mode="Markdown",
                reply_markup=kb,
            )
        except Exception as e:
            logger.error(f"❌ Admin notify failed for {admin_id}: {e}")


async def notify_new_order(bot, admin_ids, order, items):
    """Notify admins of a new order."""
    from utils.formatters import taka
    from keyboards.admin_kb import order_action_kb

    item_lines = "\n".join(
        f"  • {it['product_name']} × {it['quantity']} = {taka(it['total_price'])}"
        for it in items
    )
    text = (
        f"🔔 *নতুন অর্ডার!*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 অর্ডার: #{order['order_id']}\n"
        f"👤 নাম: {order['full_name']}\n"
        f"📞 ফোন: {order['phone']}\n"
        f"📍 ঠিকানা: {order['address']}\n"
        f"💳 পেমেন্ট: {order['payment_method'].upper()}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🛒 পণ্য:\n{item_lines}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 মোট: *{taka(order['total'])}*\n"
        f"🆔 Telegram ID: {order['user_id']}"
    )
    kb = order_action_kb(order["order_id"], "pending")
    await notify_admins(bot, admin_ids, text, kb)
