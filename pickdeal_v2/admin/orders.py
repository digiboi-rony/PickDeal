"""admin/orders.py — order list, detail, status update"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import models.order as order_model
import models.payment as payment_model
from keyboards.admin_kb import orders_list_kb, order_action_kb
from services.notification import notify_customer
from utils.formatters import order_card, taka
from middlewares.auth import is_admin
from config.settings import ORDERS_PER_PAGE

logger = logging.getLogger(__name__)


async def list_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """adm_orders_<status>_<page>"""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    parts  = query.data.split("_")   # adm, orders, status, page
    status = parts[2]
    page   = int(parts[3])

    orders = order_model.get_all(status, page, ORDERS_PER_PAGE)
    if not orders:
        await query.edit_message_text(
            f"📭 কোনো অর্ডার নেই — *{status}*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Dashboard", callback_data="adm_dashboard")
            ]])
        )
        return

    await query.edit_message_text(
        f"📋 *অর্ডার লিস্ট — {status}* (পৃষ্ঠা {page+1})\n\nঅর্ডার বেছে নিন:",
        parse_mode="Markdown",
        reply_markup=orders_list_kb(orders, status, page),
    )


async def order_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """adm_order_<order_id>"""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    order_id = int(query.data.split("_")[2])
    order    = order_model.get(order_id)
    if not order:
        await query.answer("অর্ডার পাওয়া যায়নি!", show_alert=True)
        return

    items   = order_model.get_items(order_id)
    payment = payment_model.get_by_order(order_id)
    pay_txt = f"\n💳 পেমেন্ট স্ট্যাটাস: {payment['status'].upper()}" if payment else ""

    text = order_card(order, items) + pay_txt

    await query.edit_message_text(
        f"🛠️ *অর্ডার ম্যানেজমেন্ট*\n\n{text}",
        parse_mode="Markdown",
        reply_markup=order_action_kb(order_id, order["status"]),
    )


async def update_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """adm_upd_<order_id>_<new_status>"""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    parts      = query.data.split("_")
    order_id   = int(parts[2])
    new_status = "_".join(parts[3:])  # handles: payment_confirmed, out_for_delivery etc

    order = order_model.get(order_id)
    if not order:
        await query.answer("অর্ডার পাওয়া যায়নি!", show_alert=True)
        return

    # Validate flow
    allowed = order_model.STATUS_FLOW.get(order["status"], [])
    if new_status not in allowed:
        await query.answer(f"❌ এই স্ট্যাটাস পরিবর্তন করা যাবে না!", show_alert=True)
        return

    order_model.update_status(order_id, new_status)

    # Verify payment record if confirming payment
    if new_status == "payment_confirmed":
        payment_model.verify(order_id)

    # Notify customer
    await notify_customer(context.bot, order["user_id"], order_id, new_status)

    # Reload and show updated order
    order = order_model.get(order_id)
    items = order_model.get_items(order_id)
    text  = order_card(order, items)

    from models.order import STATUS_EMOJI, STATUS_LABEL
    em  = STATUS_EMOJI.get(new_status, "")
    lbl = STATUS_LABEL.get(new_status, new_status)

    await query.edit_message_text(
        f"✅ *স্ট্যাটাস আপডেট: {em} {lbl}*\n\n{text}",
        parse_mode="Markdown",
        reply_markup=order_action_kb(order_id, new_status),
    )
