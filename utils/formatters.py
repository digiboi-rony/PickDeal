"""
utils/formatters.py
===================
All message text formatting — never build long strings in handlers.
"""

from config.settings import BOT_NAME


# ─── Status Maps ─────────────────────────────────────────────────────────────

STATUS_EMOJI = {
    "pending":    "🕐",
    "confirmed":  "✅",
    "processing": "⚙️",
    "packed":     "📦",
    "shipped":    "🚚",
    "out_for_delivery": "🛵",
    "delivered":  "✅",
    "cancelled":  "❌",
}

STATUS_LABEL = {
    "pending":    "Pending Payment",
    "confirmed":  "Payment Confirmed",
    "processing": "Being Processed",
    "packed":     "Packed",
    "shipped":    "Shipped",
    "out_for_delivery": "Out for Delivery",
    "delivered":  "Delivered",
    "cancelled":  "Cancelled",
}

STATUS_TIMELINE = [
    "pending", "confirmed", "processing", "packed", "shipped", "delivered"
]

PAYMENT_EMOJI = {"bkash": "💜", "nagad": "🟠", "cod": "💵"}


def short_status(status: str) -> str:
    e = STATUS_EMOJI.get(status, "❓")
    l = STATUS_LABEL.get(status, status.title())
    return f"{e} {l}"


def format_price(amount) -> str:
    return f"৳{int(amount):,}"


def format_product_card(product, show_full: bool = True) -> str:
    price = product["price"]
    disc  = product["discount_price"]
    stock = product["stock"]

    price_line = format_price(price)
    if disc and disc < price:
        saved = price - disc
        pct   = int((saved / price) * 100)
        price_line = f"~~৳{int(price):,}~~ → *{format_price(disc)}*  🏷️ -{pct}% OFF"

    stock_text = f"✅ In Stock ({stock} left)" if stock > 0 else "❌ Out of Stock"
    rating = ""
    if product["rating"]:
        stars = "⭐" * round(product["rating"])
        rating = f"\n⭐ *Rating:* {stars} {product['rating']}/5 ({product['review_count']} reviews)"

    tags = ""
    if product.get("tags"):
        tag_list = " ".join(f"#{t.strip()}" for t in product["tags"].split(",") if t.strip())
        tags = f"\n🏷️ {tag_list}"

    badges = ""
    if product.get("is_featured"):
        badges += " 🌟Featured"
    if product.get("is_bestseller"):
        badges += " 🔥Bestseller"

    desc = product["description"] or "No description available."

    return (
        f"🛍️ *{product['name']}*{badges}\n\n"
        f"📝 {desc}\n\n"
        f"💰 *Price:* {price_line}\n"
        f"📦 *Stock:* {stock_text}\n"
        f"🏷️ *Category:* {product['category']}"
        f"{rating}{tags}"
    )


def format_cart_summary(items: list) -> str:
    if not items:
        return "🛒 *Your cart is empty.*\n\nBrowse products to add items!"

    lines = ["🛒 *Your Shopping Cart*\n━━━━━━━━━━━━━━━━━━━━"]
    subtotal = 0
    for item in items:
        unit = item["discount_price"] or item["price"]
        total = unit * item["quantity"]
        subtotal += total
        lines.append(f"• {item['name'][:25]}\n  {format_price(unit)} × {item['quantity']} = *{format_price(total)}*")

    lines.append(f"━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"🧾 *Subtotal: {format_price(subtotal)}*")
    lines.append(f"🚚 Delivery charge added at checkout")
    return "\n".join(lines)


def format_order_card(order, items=None) -> str:
    st = short_status(order["status"])
    created = str(order["created_at"])[:16]
    items_text = order.get("items_summary") or "—"

    payment_emoji = PAYMENT_EMOJI.get(order.get("payment_method", ""), "💳")
    delivery = format_price(order.get("delivery_charge", 0))
    discount = order.get("discount", 0)
    disc_text = f"\n🎫 *Discount:* -{format_price(discount)}" if discount else ""

    return (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *Order #{order['order_id']}*\n"
        f"📦 *Items:* {items_text}\n"
        f"💰 *Subtotal:* {format_price(order['subtotal'])}\n"
        f"🚚 *Delivery:* {delivery}"
        f"{disc_text}\n"
        f"💵 *Total:* *{format_price(order['total_price'])}*\n"
        f"{payment_emoji} *Payment:* {order.get('payment_method', '—').upper()}\n"
        f"📍 *Address:* {order['address']}\n"
        f"📅 *Date:* {created}\n"
        f"🚦 *Status:* {st}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )


def format_status_timeline(current_status: str) -> str:
    if current_status == "cancelled":
        return "❌ *Order Cancelled*\n\nThis order has been cancelled."

    lines = ["📍 *Delivery Progress:*\n"]
    reached = False
    for step in STATUS_TIMELINE:
        emoji = STATUS_EMOJI.get(step, "⬜")
        label = STATUS_LABEL.get(step, step.title())
        if step == current_status:
            lines.append(f"➡️ *{emoji} {label}*  ← You are here")
            reached = True
        elif not reached:
            lines.append(f"✔️  {emoji} {label}")
        else:
            lines.append(f"⬜  {emoji} {label}")
    return "\n".join(lines)


def format_order_notification(order_id: int, new_status: str, order=None) -> str:
    msgs = {
        "confirmed": (
            f"✅ *Payment Confirmed!*\n\n"
            f"Great news! Your payment for Order *#{order_id}* has been verified. "
            f"We're preparing your order now! 📦"
        ),
        "processing": (
            f"⚙️ *Order in Processing!*\n\n"
            f"Order *#{order_id}* is currently being prepared and packed. "
            f"We'll notify you once it's shipped!"
        ),
        "packed": (
            f"📦 *Order Packed!*\n\n"
            f"Order *#{order_id}* has been packed and is ready for pickup by our courier."
        ),
        "shipped": (
            f"🚚 *Order Shipped!*\n\n"
            f"Order *#{order_id}* is on its way! "
            f"Expected delivery: 1–3 business days. 🎉"
        ),
        "out_for_delivery": (
            f"🛵 *Out for Delivery!*\n\n"
            f"Order *#{order_id}* is out for delivery today! "
            f"Please keep your phone handy. 📱"
        ),
        "delivered": (
            f"✅ *Order Delivered!*\n\n"
            f"Order *#{order_id}* has been delivered successfully. "
            f"Thank you for shopping with *{BOT_NAME}*! 🎉\n\n"
            f"We'd love your feedback. 🙏"
        ),
        "cancelled": (
            f"❌ *Order Cancelled*\n\n"
            f"Order *#{order_id}* has been cancelled.\n"
            f"If you made a payment, refund will be processed within 2–3 business days.\n"
            f"Need help? Tap Support."
        ),
    }
    return msgs.get(new_status, f"📌 Order *#{order_id}* status updated to: *{new_status.title()}*")


def format_admin_new_order(order_id: int, order_data: dict) -> str:
    payment_emoji = PAYMENT_EMOJI.get(order_data.get("payment_method", ""), "💳")
    return (
        f"🔔 *New Order Received!*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *Order ID:* #{order_id}\n"
        f"👤 *Customer:* {order_data['full_name']}\n"
        f"📞 *Phone:* {order_data['phone']}\n"
        f"📍 *Address:* {order_data['address']}\n"
        f"📦 *Items:* {order_data.get('items_summary', '—')}\n"
        f"💰 *Total:* {format_price(order_data['total_price'])}\n"
        f"{payment_emoji} *Payment:* {order_data.get('payment_method', '—').upper()}\n"
        f"👤 *User ID:* {order_data['user_id']}"
    )


def format_admin_payment_screenshot(order_id: int, order, user_id: int) -> str:
    return (
        f"💳 *Payment Screenshot*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *Order ID:* #{order_id}\n"
        f"👤 *Customer:* {order['full_name']}\n"
        f"📞 *Phone:* {order['phone']}\n"
        f"💰 *Amount:* {format_price(order['total_price'])}\n"
        f"👤 *Telegram ID:* {user_id}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"Use buttons below to confirm or reject:"
    )


def format_analytics(stats: dict, order_counts: dict, user_count: int,
                     top_products: list, daily: list) -> str:
    total_rev = stats.get("total_revenue", 0)
    today_rev = stats.get("today_revenue", 0)
    total_ord = stats.get("total_orders", 0)

    lines = [
        f"📊 *PickDeal BD Analytics*",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"👥 *Total Users:* {user_count:,}",
        f"📋 *Total Orders:* {total_ord:,}",
        f"💰 *Total Revenue:* {format_price(total_rev)}",
        f"📅 *Today Revenue:* {format_price(today_rev)}",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"📦 *Order Status Breakdown:*",
    ]
    for status, count in order_counts.items():
        e = STATUS_EMOJI.get(status, "❓")
        lines.append(f"  {e} {status.title()}: {count}")

    if top_products:
        lines.append(f"━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"🔥 *Top Products (by sales):*")
        for i, p in enumerate(top_products, 1):
            lines.append(f"  {i}. {p['name'][:22]} — {p['total_sold']} sold")

    if daily:
        lines.append(f"━━━━━━━━━━━━━━━━━━━━")
        lines.append(f"📅 *Last {len(daily)} Days Sales:*")
        for d in daily:
            lines.append(f"  📆 {d['day']}: {d['orders']} orders | {format_price(d['revenue'] or 0)}")

    return "\n".join(lines)


def format_profile(user, orders: list) -> str:
    name = f"{user['first_name']} {user['last_name'] or ''}".strip()
    username = f"@{user['username']}" if user["username"] else "—"
    joined = str(user["joined_at"])[:10]
    total = format_price(user["total_spent"] or 0)

    return (
        f"👤 *My Profile*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🙋 *Name:* {name}\n"
        f"📱 *Username:* {username}\n"
        f"📅 *Member Since:* {joined}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🛍️ *Total Orders:* {user['total_orders'] or 0}\n"
        f"💰 *Total Spent:* {total}\n"
        f"🔗 *Referral Code:* `{user['referral_code'] or '—'}`\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
