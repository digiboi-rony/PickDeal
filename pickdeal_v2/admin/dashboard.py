"""admin/dashboard.py — admin panel entry point"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import models.order as order_model
import models.user as user_model
from keyboards.admin_kb import admin_dashboard_kb
from middlewares.auth import is_admin
from utils.formatters import taka

logger = logging.getLogger(__name__)


async def dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/admin command — show dashboard"""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        if update.message:
            await update.message.reply_text("❌ আপনি এই কমান্ড ব্যবহার করতে পারবেন না।")
        elif update.callback_query:
            await update.callback_query.answer("❌ Admin only!", show_alert=True)
        return

    st = order_model.stats()
    by = st["by_status"]

    text = (
        f"🛠️ *Admin Dashboard — PickDeal BD*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 মোট ব্যবহারকারী: {user_model.count()}\n"
        f"📦 মোট অর্ডার: {st['total']}\n"
        f"💰 মোট রাজস্ব: {taka(st['revenue'])}\n"
        f"📅 আজকের অর্ডার: {st['today']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 Pending:   {by.get('pending', 0)}\n"
        f"✅ Confirmed: {by.get('payment_confirmed', 0)}\n"
        f"⚙️ Processing:{by.get('processing', 0)}\n"
        f"🚚 Shipping:  {by.get('shipping', 0)}\n"
        f"🎉 Delivered: {by.get('delivered', 0)}\n"
        f"❌ Cancelled: {by.get('cancelled', 0)}"
    )

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text, parse_mode="Markdown", reply_markup=admin_dashboard_kb()
        )
    else:
        await update.message.reply_text(
            text, parse_mode="Markdown", reply_markup=admin_dashboard_kb()
        )
