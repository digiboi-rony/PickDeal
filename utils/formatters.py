"""
utils/formatters.py — PickDeal BD v3.1 FIXED
BUG FIX: sqlite3.Row has no .get() method — use dict(row) or row[key] with fallback.
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
STATUS_FLOW = ["pending","confirmed","processing","packed","shipped","out_for_delivery","delivered"]


def _r(row, key, default=None):
    """Safe row accessor — works for both sqlite3.Row and dict."""
    try:
        val = row[key]
        return val if val is not None else default
    except (KeyError, IndexError):
        return default


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
    price = float(_r(product, "price", 0))
    disc  = _r(product, "discount_price")
    disc  = float(disc) if disc else None
    stock = int(_r(product, "stock", 0))

    if disc and disc < price:
        saved = price - disc
        pct   = int((saved / price) * 100)
        price_line = f"~~৳{int(price):,}~~ → *{format_price(disc)}*  🏷️ -{pct}% OFF"
    else:
        price_line = f"*{format_price(price)}*"

    if stock > 5:
        stock_text = f"✅ স্টকে আছে ({stock} টি)"
    elif 0 < stock <= 5:
        stock_text = f"⚠️ সীমিত স্টক ({stock} টি)"
    else:
        stock_text = "❌ স্টক নেই"

    badges = ""
    if _r(product, "is_featured"):   badges += " 🌟Featured"
    if _r(product, "is_bestseller"): badges += " 🔥Bestseller"

    rating_str = ""
    rating = _r(product, "rating")
    if rating:
        stars = "⭐" * round(float(rating))
        rating_str = f"\n⭐ *রেটিং:* {stars} {rating}/5"

    tags_str = ""
    tags = _r(product, "tags", "")
    if tags:
        tag_list = " ".join(f"#{t.strip()}" for t in str(tags).split(",") if t.strip())
        if tag_list:
            tags_str = f"\n🏷️ {tag_list}"

    cod_str = ""
    if _r(product, "cod_available") == 0:
        cod_str = "\n⚠️ *COD পাওয়া যাবে না*"

    adv_str = ""
    adv = _r(product, "advance_pct", 0)
    if adv and float(adv) > 0:
        adv_str = f"\n💰 *অগ্রিম:* {int(float(adv))}% পেমেন্ট লাগবে"

    desc = _r(product, "description") or "কোনো বিবরণ নেই।"
    name = _r(product, "name", "পণ্য")
    category = _r(product, "category", "—")

    return (
        f"🛍️ *{name}*{badges}\n\n"
        f"📝 {desc}\n\n"
        f"💰 *মূল্য:* {price_line}\n"
        f"📦 *স্টক:* {stock_text}\n"
        f"🏷️ *ক্যাটাগরি:* {category}"
        f"{rating_str}{tags_str}{cod_str}{adv_str}"
    )


def format_cart_summary(items: list) -> str:
    if not items:
        return "🛒 *আপনার কার্ট খালি*\n\nপণ্য ব্রাউজ করুন এবং কার্টে যোগ করুন!"
    lines = ["🛒 *আপনার শপিং কার্ট*\n━━━━━━━━━━━━━━━━━━━━"]
    subtotal = 0
    for item in items:
        unit  = float(_r(item, "discount_price") or _r(item, "price", 0))
        qty   = int(_r(item, "quantity", 1))
        total = unit * qty
        subtotal += total
        name = _r(item, "name", "পণ্য")
        lines.append(f"• {name[:25]}\n  {format_price(unit)} × {qty} = *{format_price(total)}*")
    lines.append("━━━━━━━━━━━━━━━━━━━━")
    lines.append(f"🧾 *সাবটোটাল: {format_price(subtotal)}*")
    lines.append("🚚 ডেলিভারি চার্জ চেকআউটে যোগ হবে")
    return "\n".join(lines)


def format_order_card(order) -> str:
    status   = _r(order, "status", "pending")
    st       = short_status(status)
    created  = str(_r(order, "created_at", ""))[:16]
    disc     = float(_r(order, "discount", 0) or 0)
    adv      = float(_r(order, "advance_amount", 0) or 0)
    subtotal = float(_r(order, "subtotal", 0) or 0)
    total    = float(_r(order, "total_price", 0) or 0)
    dcharge  = float(_r(order, "delivery_charge", 0) or 0)
    dmethod  = _r(order, "delivery_method", "—")
    pm       = str(_r(order, "payment_method", "—") or "—")
    fname    = _r(order, "full_name", "—")
    phone    = _r(order, "phone", "—")
    address  = _r(order, "address", "—")
    notes    = _r(order, "notes")
    anote    = _r(order, "admin_note")
    oid      = _r(order, "order_id", "?")
    isummary = _r(order, "items_summary", "—")

    pm_map = {"bkash":"💜 bKash","nagad":"🟠 Nagad","rocket":"🟣 Rocket","cash on delivery":"💵 COD","pending":"⏳ নির্বাচন বাকি"}
    pm_label = pm_map.get(pm.lower(), f"💳 {pm}")

    disc_line  = f"\n🎫 *ডিসকাউন্ট:* -{format_price(disc)}" if disc else ""
    adv_line   = f"\n💰 *অগ্রিম:* {format_price(adv)}" if adv else ""
    notes_line = f"\n📝 *নোট:* {notes}" if notes else ""
    anote_line = f"\n🛠️ *Admin নোট:* {anote}" if anote else ""

    return (
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 *অর্ডার #{oid}*\n"
        f"📦 *পণ্য:* {isummary}\n"
        f"💰 *সাবটোটাল:* {format_price(subtotal)}\n"
        f"🚚 *ডেলিভারি:* {format_price(dcharge)} ({dmethod})"
        f"{disc_line}\n"
        f"💵 *মোট: {format_price(total)}*"
        f"{adv_line}\n"
        f"{pm_label}\n"
        f"👤 *নাম:* {fname}\n"
        f"📞 *ফোন:* {phone}\n"
        f"📍 *ঠিকানা:* {address}"
        f"{notes_line}\n"
        f"📅 *তারিখ:* {created}\n"
        f"🚦 *স্ট্যাটাস:* {st}"
        f"{anote_line}\n"
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
        "confirmed": f"✅ *পেমেন্ট নিশ্চিত!*\n\nঅর্ডার *#{order_id}* এর পেমেন্ট ভেরিফাই হয়েছে। আমরা প্রস্তুত করছি! 📦",
        "processing": f"⚙️ *প্রসেস হচ্ছে!*\n\nঅর্ডার *#{order_id}* প্যাক করা হচ্ছে। শীঘ্রই শিপ হবে!",
        "packed": f"📦 *প্যাক সম্পন্ন!*\n\nঅর্ডার *#{order_id}* কুরিয়ার পিকআপের জন্য প্রস্তুত।",
        "shipped": f"🚚 *শিপ হয়েছে!*\n\nঅর্ডার *#{order_id}* পথে আছে! ১-৩ কার্যদিবসে পাবেন। 🎉",
        "out_for_delivery": f"🛵 *ডেলিভারিতে বের হয়েছে!*\n\nঅর্ডার *#{order_id}* আজ ডেলিভারি হবে! ফোন কাছে রাখুন। 📱",
        "delivered": f"🎉 *ডেলিভারি সম্পন্ন!*\n\nঅর্ডার *#{order_id}* পেয়েছেন। *{BOT_NAME}* থেকে কেনার জন্য ধন্যবাদ! 🙏",
        "cancelled": f"❌ *বাতিল হয়েছে*\n\nঅর্ডার *#{order_id}* বাতিল। পেমেন্ট করলে ২-৩ দিনে ফেরত পাবেন।",
        "refunded": f"↩️ *রিফান্ড হচ্ছে*\n\nঅর্ডার *#{order_id}* এর রিফান্ড ২-৩ কার্যদিবসে পাবেন।",
    }
    return msgs.get(new_status, f"📌 অর্ডার *#{order_id}* → *{STATUS_LABEL.get(new_status, new_status)}*")


def format_admin_new_order(order_id: int, data: dict) -> str:
    return (
        f"🔔 *নতুন অর্ডার!*\n━━━━━━━━━━━━━━━━━━━━\n"
        f"🆔 Order: *#{order_id}*\n"
        f"👤 Customer: {data.get('full_name','—')}\n"
        f"📞 Phone: {data.get('phone','—')}\n"
        f"📍 Address: {data.get('address','—')}\n"
        f"🚚 Delivery: {data.get('delivery_method','—')}\n"
        f"📦 Items: {data.get('items_summary','—')}\n"
        f"💰 Total: *{format_price(data.get('total_price',0))}*\n"
        f"👤 User ID: `{data.get('user_id','—')}`"
    )


def format_analytics(stats: dict, order_counts: dict, user_count: int,
                     top_products: list, daily: list) -> str:
    lines = [
        f"📊 *Analytics — {BOT_NAME}*",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"👥 *মোট ইউজার:* {user_count:,}",
        f"📋 *মোট অর্ডার:* {stats.get('total_orders',0):,}",
        f"💰 *মোট রেভিনিউ:* {format_price(stats.get('total_revenue',0))}",
        f"📅 *আজকের রেভিনিউ:* {format_price(stats.get('today_revenue',0))}",
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
            lines.append(f"  {i}. {_r(p,'name','?')[:22]} — {_r(p,'total_sold',0)} বিক্রি")
    if daily:
        lines += [f"━━━━━━━━━━━━━━━━━━━━", f"📅 *শেষ {len(daily)} দিনের বিক্রি:*"]
        for d in daily:
            lines.append(f"  📆 {_r(d,'day','?')}: {_r(d,'orders',0)} অর্ডার | {format_price(_r(d,'revenue',0) or 0)}")
    return "\n".join(lines)


def format_profile(user, orders: list) -> str:
    fname  = _r(user, "first_name", "")
    lname  = _r(user, "last_name", "") or ""
    name   = f"{fname} {lname}".strip() or "—"
    uname  = f"@{_r(user,'username','')}" if _r(user,"username") else "—"
    joined = str(_r(user, "joined_at", ""))[:10]
    total_orders = _r(user, "total_orders", 0) or 0
    total_spent  = _r(user, "total_spent", 0) or 0
    ref_code     = _r(user, "referral_code", "—") or "—"
    return (
        f"👤 *আমার প্রোফাইল*\n━━━━━━━━━━━━━━━━━━━━\n"
        f"🙋 *নাম:* {name}\n"
        f"📱 *Username:* {uname}\n"
        f"📅 *যোগদান:* {joined}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🛍️ *মোট অর্ডার:* {total_orders}\n"
        f"💰 *মোট খরচ:* {format_price(total_spent)}\n"
        f"🔗 *রেফারেল কোড:* `{ref_code}`\n"
        f"━━━━━━━━━━━━━━━━━━━━"
    )
