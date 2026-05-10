"""
utils/formatters.py — PickDeal BD v3
All message text builders. Handlers stay clean.
"""

from config.settings import BOT_NAME

STATUS_EMOJI = {
    "pending":           "🕐",
    "awaiting_payment":  "💳",
    "confirmed":         "✅",
    "processing":        "⚙️",
    "packed":            "📦",
    "shipped":           "🚚",
    "out_for_delivery":  "🛵",
    "delivered":         "🎉",
    "cancelled":         "❌",
    "refunded":          "↩️",
}
STATUS_LABEL = {
    "pending":           "অপেক্ষমাণ",
    "awaiting_payment":  "পেমেন্টের অপেক্ষায়",
    "confirmed":         "পেমেন্ট নিশ্চিত",
    "processing":        "প্রসেস হচ্ছে",
    "packed":            "প্যাক করা হয়েছে",
    "shipped":           "শিপমেন্ট হয়েছে",
    "out_for_delivery":  "ডেলিভারিতে আছে",
    "delivered":         "ডেলিভারি সম্পন্ন",
    "cancelled":         "বাতিল",
    "refunded":          "রিফান্ড হয়েছে",
}
STATUS_FLOW = [
    "pending", "confirmed", "processing", "packed",
    "shipped", "out_for_delivery", "delivered"
]


def short_status(status: str) -> str:
    e = STATUS_EMOJI.get(status, "❓")
    l = STATUS_LABEL.get(status, status)
    return f"{e} {l}"


def format_price(amount) -> str:
    try:
        return f"৳{int(float(amount)):,}"
    except (TypeError, ValueError):
        return "৳0"


def format_product_card(product) -> str:
    price = float(product["price"])
    disc  = float(product["discount_price"]) if product["discount_price"] else None
    stock = int(product["stock"])

    if disc and disc < price:
        saved = price - disc
        pct   = int((saved / price) * 100)
        price_line = f"~~৳{int(price):,}~~ → *{format_price(disc)}*  🏷️ -{pct}% OFF"
    else:
        price_line = f"*{format_price(price)}*"

    stock_text = (
        f"✅ স্টকে আছে ({stock} টি)" if stock > 5
        else f"⚠️ সীমিত স্টক ({stock} টি)" if 0 < stock <= 5
        else "❌ স্টক নেই"
    )

    badges = ""
    if product.get("is_featured"):   badges += " 🌟Featured"
    if product.get("is_bestseller"): badges += " 🔥Bestseller"

    rating_str = ""
    if product.get("rating"):
        stars = "⭐" * round(float(product["rating"]))
        rating_str = f"\n⭐ *রেটিং:* {stars} {product['rating']}/5"

    tags_str = ""
    if product.get("tags"):
        tags_str = "\n🏷️ " + " ".join(f"#{t.strip()}" for t in product["tags"].split(",") if t.strip())

    cod_str = ""
    if product.get("cod_available") == 0:
        cod_str = "\n⚠️ *COD পাওয়া যাবে না* — অগ্রিম পেমেন্ট বাধ্যতামূলক"

    adv_str = ""
    if product.get("advance_pct") and float(product["advance_pct"]) > 0:
        adv_str = f"\n💰 *অগ্রিম:* {int(product['advance_pct'])}% অগ্রিম পেমেন্ট লাগবে"

    desc = product.get("description") or "কোনো বিবরণ নেই।"

    return (
        f"🛍️ *{product['name']}*{badges}\n\n"
        f"📝 {desc}\n\n"
        f"💰 *মূল্য:* {price_line}\n"
        f"📦 *স্টক:* {stock_text}\n"
        f"🏷️ *ক্যাটাগরি:* {product['category']}"
        f"{rating_str}{tags_str}{cod_str}{adv_str}"
    )


def format_cart_summary(items: list) -> str:
    if not items:
        return (
            "🛒 *আপনার কার্ট খালি*\n\n"
            "পণ্য ব্রাউজ করুন এবং কার্টে যোগ করুন!"
        )
    lines = ["🛒 *আপনার শপিং কার্ট*\n━━━━━━━━━━━━━━━━━━━━"]
    subtotal = 0
    for item in items:
        unit  = float(item["discount_price"] or item["price"])
        total = unit * int(item["quantity"])
        subtotal += total
        lines.append(
            f"• {item['name'][:25]}\n"
            f"  {format_price(unit)} × {item['quantity']} = *{format_price(total)}*"
        )
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"🧾 *সাবটোটাল: {format_price(subtotal)}*")
    lines.append("🚚 ডেলিভারি চার্জ চেকআউটে যোগ হবে")
    return "\n".join(lines)


def format_order_card(order) -> str:
    st      = short_status(order["status"])
    created = str(order["created_at"])[:16]
    disc    = float(order.get("discount", 0))
    adv     = float(order.get("advance_amount", 0))
    pm_map  = {"bkash": "💜 bKash", "nagad": "🟠 Nagad",
               "rocket": "🟣 Rocket", "cash on delivery": "💵 COD"}
    pm = pm_map.get(str(order.get("payment_method", "")).lower(), "💳 " + str(order.get("payment_method", "—")))

    disc_line = f"\n🎫 *ডিসকাউন্ট:* -{format_price(disc)}" if disc else ""
    adv_line  = f"\n💰 *অগ্রিম পেমেন্ট:* {format_price(adv)}" if adv else ""
    note_line = f"\n📝 *নোট:* {order.get('notes')}" if order.get("notes") else ""
    admin_note = f"\n🛠️ *Admin নোট:* {order.get('admin_note')}" if order.get("admin_note") else ""

    return (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *অর্ডার #{order['order_id']}*\n"
        f"📦 *পণ্য:* {order.get('items_summary', '—')}\n"
        f"💰 *সাবটোটাল:* {format_price(order['subtotal'])}\n"
        f"🚚 *ডেলিভারি:* {format_price(order.get('delivery_charge', 0))} ({order.get('delivery_method', '—')})"
        f"{disc_line}\n"
        f"💵 *মোট: {format_price(order['total_price'])}*"
        f"{adv_line}\n"
        f"{pm} *পেমেন্ট পদ্ধতি*\n"
        f"👤 *নাম:* {order['full_name']}\n"
        f"📞 *ফোন:* {order['phone']}\n"
        f"📍 *ঠিকানা:* {order['address']}"
        f"{note_line}\n"
        f"📅 *তারিখ:* {created}\n"
        f"🚦 *স্ট্যাটাস:* {st}"
        f"{admin_note}\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )


def format_status_timeline(current_status: str) -> str:
    if current_status in ("cancelled", "refunded"):
        e = STATUS_EMOJI.get(current_status, "❌")
        l = STATUS_LABEL.get(current_status, current_status)
        return f"{e} *{l}*\n\nএই অর্ডারটি {l} হয়েছে।"
    lines = ["📍 *ডেলিভারি অগ্রগতি:*\n"]
    reached = False
    for step in STATUS_FLOW:
        e = STATUS_EMOJI.get(step, "⬜")
        l = STATUS_LABEL.get(step, step)
        if step == current_status:
            lines.append(f"▶️ *{e} {l}*  ◀ এখানে আছেন")
            reached = True
        elif not reached:
            lines.append(f"✔️  {e} {l}")
        else:
            lines.append(f"⬜  {e} {l}")
    return "\n".join(lines)


def format_order_notification(order_id: int, new_status: str) -> str:
    msgs = {
        "confirmed": (
            f"✅ *পেমেন্ট নিশ্চিত হয়েছে!*\n\n"
            f"অর্ডার *#{order_id}* এর পেমেন্ট ভেরিফাই হয়েছে। "
            f"আমরা আপনার পণ্য প্রস্তুত করছি! 📦"
        ),
        "processing": (
            f"⚙️ *অর্ডার প্রসেস হচ্ছে!*\n\n"
            f"অর্ডার *#{order_id}* প্যাক করা হচ্ছে। শীঘ্রই শিপ করা হবে!"
        ),
        "packed": (
            f"📦 *অর্ডার প্যাক হয়েছে!*\n\n"
            f"অর্ডার *#{order_id}* প্যাক সম্পন্ন। কুরিয়ার পিকআপের জন্য প্রস্তুত।"
        ),
        "shipped": (
            f"🚚 *অর্ডার শিপ হয়েছে!*\n\n"
            f"অর্ডার *#{order_id}* পথে আছে! ১-৩ কার্যদিবসে পাবেন। 🎉"
        ),
        "out_for_delivery": (
            f"🛵 *ডেলিভারিতে বের হয়েছে!*\n\n"
            f"অর্ডার *#{order_id}* আজ ডেলিভারি হবে! ফোন কাছে রাখুন। 📱"
        ),
        "delivered": (
            f"🎉 *ডেলিভারি সম্পন্ন!*\n\n"
            f"অর্ডার *#{order_id}* ডেলিভারি হয়েছে। "
            f"*{BOT_NAME}* থেকে কেনার জন্য ধন্যবাদ! 🙏\n\n"
            f"আপনার মতামত আমাদের কাছে গুরুত্বপূর্ণ।"
        ),
        "cancelled": (
            f"❌ *অর্ডার বাতিল হয়েছে*\n\n"
            f"অর্ডার *#{order_id}* বাতিল করা হয়েছে।\n"
            f"পেমেন্ট করে থাকলে ২-৩ কার্যদিবসে ফেরত পাবেন।\n"
            f"সাহায্যের জন্য Support ট্যাপ করুন।"
        ),
        "refunded": (
            f"↩️ *রিফান্ড প্রক্রিয়া শুরু হয়েছে*\n\n"
            f"অর্ডার *#{order_id}* এর রিফান্ড ২-৩ কার্যদিবসে আপনার একাউন্টে যাবে।"
        ),
    }
    return msgs.get(new_status,
        f"📌 অর্ডার *#{order_id}* স্ট্যাটাস আপডেট: *{STATUS_LABEL.get(new_status, new_status)}*"
    )


def format_admin_new_order(order_id: int, data: dict) -> str:
    pm = data.get("payment_method", "—")
    return (
        f"🔔 *নতুন অর্ডার!*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 Order ID: *#{order_id}*\n"
        f"👤 Customer: {data['full_name']}\n"
        f"📞 Phone: {data['phone']}\n"
        f"📍 Address: {data['address']}\n"
        f"🚚 Delivery: {data.get('delivery_method', '—')}\n"
        f"📦 Items: {data.get('items_summary', '—')}\n"
        f"💰 Total: *{format_price(data['total_price'])}*\n"
        f"💳 Payment: {pm.upper()}\n"
        f"👤 User ID: `{data['user_id']}`"
    )


def format_analytics(stats: dict, order_counts: dict, user_count: int,
                     top_products: list, daily: list) -> str:
    lines = [
        f"📊 *Analytics — {BOT_NAME}*",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"👥 *মোট ইউজার:* {user_count:,}",
        f"📋 *মোট অর্ডার:* {stats.get('total_orders', 0):,}",
        f"💰 *মোট রেভিনিউ:* {format_price(stats.get('total_revenue', 0))}",
        f"📅 *আজকের রেভিনিউ:* {format_price(stats.get('today_revenue', 0))}",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"📦 *অর্ডার স্ট্যাটাস:*",
    ]
    for status, count in order_counts.items():
        e = STATUS_EMOJI.get(status, "❓")
        l = STATUS_LABEL.get(status, status)
        lines.append(f"  {e} {l}: {count}")

    if top_products:
        lines += [f"━━━━━━━━━━━━━━━━━━━━", f"🔥 *টপ পণ্য:*"]
        for i, p in enumerate(top_products, 1):
            lines.append(f"  {i}. {p['name'][:22]} — {p['total_sold']} বিক্রি")

    if daily:
        lines += [f"━━━━━━━━━━━━━━━━━━━━", f"📅 *শেষ {len(daily)} দিনের বিক্রি:*"]
        for d in daily:
            lines.append(f"  📆 {d['day']}: {d['orders']} অর্ডার | {format_price(d['revenue'] or 0)}")

    return "\n".join(lines)


def format_profile(user, orders: list) -> str:
    name  = f"{user['first_name']} {user['last_name'] or ''}".strip()
    uname = f"@{user['username']}" if user["username"] else "—"
    joined = str(user["joined_at"])[:10]
    return (
        f"👤 *আমার প্রোফাইল*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🙋 *নাম:* {name}\n"
        f"📱 *Username:* {uname}\n"
        f"📅 *যোগদান:* {joined}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🛍️ *মোট অর্ডার:* {user['total_orders'] or 0}\n"
        f"💰 *মোট খরচ:* {format_price(user['total_spent'] or 0)}\n"
        f"🔗 *রেফারেল কোড:* `{user['referral_code'] or '—'}`\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
