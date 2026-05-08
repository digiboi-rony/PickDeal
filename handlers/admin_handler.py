"""
handlers/admin_handler.py
==========================
Admin-only features:
- View and manage all orders
- Update order status
- Search orders by ID
- Broadcast messages to all users
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from database.queries import (
    get_all_orders, get_order, update_order_status,
    count_orders_by_status, get_all_users,
)
from utils.helpers import (
    is_admin, format_price, format_order_status,
    format_order_card, STATUS_FLOW, STATUS_LABELS,
)

logger = logging.getLogger(__name__)

# Conversation state for broadcast
BROADCAST = 30

# How many orders to show per page in admin panel
PAGE_SIZE = 5


def admin_only(func):
    """Decorator to restrict handler to admins only."""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if not is_admin(user_id):
            if update.callback_query:
                await update.callback_query.answer("❌ Admin only!", show_alert=True)
            else:
                await update.message.reply_text("❌ You are not authorized to use admin commands.")
            return
        return await func(update, context)
    return wrapper


@admin_only
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the admin dashboard with order statistics."""
    counts = count_orders_by_status()
    total  = sum(counts.values())

    stats_text = (
        f"🛠️ *Admin Panel — PickDeal BD*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Order Statistics:*\n\n"
        f"🕐 Pending:    {counts.get('pending', 0)}\n"
        f"✅ Confirmed:  {counts.get('confirmed', 0)}\n"
        f"⚙️ Processing: {counts.get('processing', 0)}\n"
        f"🚚 Shipped:    {counts.get('shipped', 0)}\n"
        f"📦 Delivered:  {counts.get('delivered', 0)}\n"
        f"❌ Cancelled:  {counts.get('cancelled', 0)}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 *Total Orders:* {total}"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📋 All Orders",     callback_data="admin_orders_all_0"),
            InlineKeyboardButton("🕐 Pending",        callback_data="admin_orders_pending_0"),
        ],
        [
            InlineKeyboardButton("✅ Confirmed",      callback_data="admin_orders_confirmed_0"),
            InlineKeyboardButton("🚚 Shipped",        callback_data="admin_orders_shipped_0"),
        ],
        [
            InlineKeyboardButton("🔍 Search by ID",  callback_data="admin_search"),
            InlineKeyboardButton("📢 Broadcast",     callback_data="admin_broadcast"),
        ],
    ])

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            stats_text, parse_mode="Markdown", reply_markup=keyboard
        )
    else:
        await update.message.reply_text(
            stats_text, parse_mode="Markdown", reply_markup=keyboard
        )


@admin_only
async def admin_view_orders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show paginated list of orders filtered by status.
    Callback pattern: admin_orders_<status>_<page>
    """
    query = update.callback_query
    await query.answer()

    # Parse callback data: "admin_orders_pending_0"
    parts  = query.data.split("_")  # ['admin', 'orders', 'status', 'page']
    status = parts[2]               # "all", "pending", etc.
    page   = int(parts[3])          # 0-indexed page number
    offset = page * PAGE_SIZE

    orders = get_all_orders(status_filter=status, limit=PAGE_SIZE, offset=offset)

    if not orders:
        await query.edit_message_text(
            f"📭 No orders found for status: *{status}*",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Admin Panel", callback_data="admin_panel")
            ]])
        )
        return

    # Build list of order buttons
    buttons = []
    for o in orders:
        status_icon = format_order_status(o["status"])
        label = f"#{o['order_id']} | {o['first_name']} | {o['product_name'][:15]} | {status_icon}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"admin_update_{o['order_id']}_view")])

    # Pagination buttons
    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"admin_orders_{status}_{page-1}"))
    if len(orders) == PAGE_SIZE:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"admin_orders_{status}_{page+1}"))
    if nav_row:
        buttons.append(nav_row)

    buttons.append([InlineKeyboardButton("⬅️ Admin Panel", callback_data="admin_panel")])

    await query.edit_message_text(
        f"📋 *Orders — {status.title()}* (Page {page + 1})\n\nTap an order to manage it:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


@admin_only
async def admin_update_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    View order details and update status.
    Callback pattern: admin_update_<order_id>_<action>
    Actions: view | confirmed | processing | shipped | delivered | cancelled
    """
    query = update.callback_query
    await query.answer()

    parts    = query.data.split("_")
    order_id = int(parts[2])
    action   = parts[3]

    order = get_order(order_id)
    if not order:
        await query.answer(f"❌ Order #{order_id} not found!", show_alert=True)
        return

    # If it's an action (not just 'view'), update the status
    if action != "view":
        update_order_status(order_id, action)

        # Notify the customer
        customer_msg = _build_customer_notification(order_id, action, order)
        try:
            await context.bot.send_message(
                chat_id    = order["user_id"],
                text       = customer_msg,
                parse_mode = "Markdown",
                reply_markup = InlineKeyboardMarkup([[
                    InlineKeyboardButton("📋 My Orders", callback_data="my_orders")
                ]])
            )
        except Exception as e:
            logger.error(f"Failed to notify customer {order['user_id']}: {e}")

        # Reload order with new status
        order = get_order(order_id)

    # Build order detail view
    order_text = format_order_card(order)

    # Build action buttons based on current status
    current_status = order["status"]
    next_statuses  = STATUS_FLOW.get(current_status, [])

    buttons = []
    for next_status in next_statuses:
        label = STATUS_LABELS.get(next_status, next_status.title())
        buttons.append([InlineKeyboardButton(label, callback_data=f"admin_update_{order_id}_{next_status}")])

    buttons.append([InlineKeyboardButton("⬅️ Back to Orders", callback_data="admin_orders_all_0")])

    await query.edit_message_text(
        f"🛠️ *Order Details*\n\n{order_text}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


def _build_customer_notification(order_id: int, new_status: str, order) -> str:
    """Build a customer-facing status update message."""
    messages = {
        "confirmed":  (
            f"✅ *Payment Confirmed!*\n\n"
            f"Your payment for Order #{order_id} has been verified.\n"
            f"We're preparing your order now! 📦"
        ),
        "processing": (
            f"⚙️ *Order Processing!*\n\n"
            f"Order #{order_id} is being prepared for shipment."
        ),
        "shipped": (
            f"🚚 *Order Shipped!*\n\n"
            f"Order #{order_id} is on its way to you!\n"
            f"Expected delivery: 1-3 business days."
        ),
        "delivered": (
            f"📦 *Order Delivered!*\n\n"
            f"Order #{order_id} has been delivered.\n"
            f"Thank you for shopping with PickDeal BD! 🎉\n\n"
            f"Please rate your experience."
        ),
        "cancelled": (
            f"❌ *Order Cancelled*\n\n"
            f"Order #{order_id} has been cancelled.\n"
            f"If you paid, refund will be processed within 2-3 days.\n"
            f"Contact support for help."
        ),
    }
    return messages.get(new_status, f"Order #{order_id} status updated to: {new_status}")


@admin_only
async def admin_search_order(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt admin to enter an order ID."""
    query = update.callback_query
    await query.answer()

    context.user_data["admin_searching"] = True

    await query.edit_message_text(
        "🔍 *Search Order by ID*\n\n"
        "Please send the order ID number:\n"
        "_(Example: 42)_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Cancel", callback_data="admin_panel")
        ]])
    )


# ─── Broadcast Feature ───────────────────────────────────────────────────────

@admin_only
async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt admin to enter broadcast message."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "📢 *Broadcast Message*\n\n"
        "Send a message to ALL users.\n"
        "Please type the message below:\n\n"
        "_(Markdown formatting supported)_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")
        ]])
    )
    return BROADCAST


@admin_only
async def admin_send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send broadcast message to all users."""
    message_text = update.message.text
    user_ids = get_all_users()

    sent = 0
    failed = 0

    await update.message.reply_text(
        f"📢 Sending broadcast to {len(user_ids)} users...\nPlease wait."
    )

    for uid in user_ids:
        try:
            await context.bot.send_message(
                chat_id    = uid,
                text       = f"📢 *PickDeal BD Announcement*\n\n{message_text}",
                parse_mode = "Markdown",
            )
            sent += 1
        except Exception:
            failed += 1

    await update.message.reply_text(
        f"✅ *Broadcast Complete!*\n\n"
        f"✔️ Sent: {sent}\n"
        f"❌ Failed: {failed}",
        parse_mode="Markdown",
    )
    return ConversationHandler.END
