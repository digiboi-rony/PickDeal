"""utils/formatters.py — all message formatting functions"""
from models.order import STATUS_EMOJI, STATUS_LABEL
from config.settings import DELIVERY_CHARGE_DHAKA, DELIVERY_CHARGE_OUTSIDE


def taka(amount) -> str:
    """Format amount as Bangladeshi Taka."""
    return f"৳{float(amount):,.0f}"


def product_card(p, show_order_btn=True) -> str:
    """Format a product as a rich message card."""
    eff   = p["discount_price"] if p["discount_price"] else p["price"]
    price_line = (
        f"~~{taka(p['price'])}~~ → *{taka(eff)}*"
        if p["discount_price"]
        else f"*{taka(p['price'])}*"
    )
    disc_pct = ""
    if p["discount_price"]:
        pct = int((p["price"] - p["discount_price"]) / p["price"] * 100)
        disc_pct = f"  🏷️ *{pct}% OFF*"

    stock_txt = (
        "✅ স্টকে আছে"
        if p["stock"] > 10
        else f"⚠️ মাত্র {p['stock']}টি বাকি"
        if p["stock"] > 0
        else "❌ স্টক শেষ"
    )

    badges = []
    if p["is_featured"]:   badges.append("⭐ Featured")
    if p["is_bestseller"]: badges.append("🔥 Bestseller")
    badge_line = "  ".join(badges)

    lines = [
        f"🛍️ *{p['name']}*",
        f"{badge_line}" if badge_line else "",
        "",
        p["description"] or "",
        "",
        f"💰 মূল্য: {price_line}{disc_pct}",
        f"📦 স্টক: {stock_txt}",
        f"🏷️ ক্যাটাগরি: {p.get('cat_emoji','🛍️')} {p.get('cat_name', '')}",
    ]
    return "\n".join(l for l in lines if l is not None)


def order_card(o, items=None) -> str:
    """Format order detail card."""
    status = o["status"]
    emoji  = STATUS_EMOJI.get(status, "❓")
    label  = STATUS_LABEL.get(status, status)

    lines = [
        f"🆔 *অর্ডার #{o['order_id']}*",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"👤 নাম: {o['full_name']}",
        f"📞 ফোন: {o['phone']}",
        f"📍 ঠিকানা: {o['address']}",
    ]
    if o.get("notes"):
        lines.append(f"📝 নোট: {o['notes']}")

    lines += ["━━━━━━━━━━━━━━━━━━━━"]

    if items:
        lines.append("🛒 *পণ্য সমূহ:*")
        for it in items:
            lines.append(f"  • {it['product_name']} × {it['quantity']} = {taka(it['total_price'])}")
        lines.append("")

    lines += [
        f"💵 সাবটোটাল: {taka(o['subtotal'])}",
        f"🚚 ডেলিভারি: {taka(o['delivery_fee'])}",
    ]
    if o["discount"] > 0:
        lines.append(f"🎫 ডিসকাউন্ট: -{taka(o['discount'])}")
    lines += [
        f"💰 *মোট: {taka(o['total'])}*",
        f"💳 পেমেন্ট: {o['payment_method'].upper()}",
        f"━━━━━━━━━━━━━━━━━━━━",
        f"🚦 *স্ট্যাটাস: {emoji} {label}*",
        f"📅 {o['created_at'][:16]}",
    ]
    return "\n".join(lines)


def order_status_timeline(current_status: str) -> str:
    """Visual delivery progress bar."""
    flow = [
        ("pending",           "🕐", "অর্ডার হয়েছে"),
        ("payment_confirmed", "✅", "পেমেন্ট নিশ্চিত"),
        ("processing",        "⚙️", "প্রসেসিং"),
        ("packed",            "📦", "প্যাক হয়েছে"),
        ("shipping",          "🚚", "শিপিং"),
        ("out_for_delivery",  "🛵", "ডেলিভারিতে"),
        ("delivered",         "🎉", "ডেলিভারি হয়েছে"),
    ]
    if current_status == "cancelled":
        return "❌ *অর্ডার বাতিল হয়েছে।*"

    lines = ["📍 *ডেলিভারি ট্র্যাক:*\n"]
    reached = False
    for key, em, label in flow:
        if key == current_status:
            lines.append(f"➡️ *{em} {label}*  ← এখানে আছেন")
            reached = True
        elif not reached:
            lines.append(f"✔️  {em} {label}")
        else:
            lines.append(f"⬜  {em} {label}")
    return "\n".join(lines)


def cart_summary(items) -> str:
    """Format cart as a readable summary."""
    if not items:
        return "🛒 কার্ট খালি।"
    lines = ["🛒 *আপনার কার্ট:*\n━━━━━━━━━━━━━━━━━━━━"]
    total = 0
    for it in items:
        ep = float(it["eff_price"])
        line_total = ep * it["quantity"]
        total += line_total
        lines.append(f"• *{it['name']}*\n  {it['quantity']} × {taka(ep)} = {taka(line_total)}")
    lines += ["━━━━━━━━━━━━━━━━━━━━", f"💰 *সাবটোটাল: {taka(total)}*"]
    return "\n".join(lines)
