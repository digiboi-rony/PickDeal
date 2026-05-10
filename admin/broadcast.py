"""admin/broadcast.py — broadcast + analytics + coupon management"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

import models.user as user_model
import models.coupon as coupon_model
import models.order as order_model
from middlewares.auth import is_admin
from utils.formatters import taka

logger = logging.getLogger(__name__)

BROADCAST_TEXT = 500
COUPON_INPUT   = 501


# ─── Broadcast ───────────────────────────────────────────────────────────────

async def start_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    await query.edit_message_text(
        "📢 *ব্রডকাস্ট মেসেজ*\n\n"
        "সকল ব্যবহারকারীকে পাঠানোর বার্তা লিখুন:\n"
        "_(Markdown ফরম্যাট সাপোর্টেড)_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ বাতিল", callback_data="adm_dashboard")
        ]])
    )
    return BROADCAST_TEXT


async def send_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END

    message_text = update.message.text
    user_ids     = user_model.get_all_ids()
    sent = failed = 0

    status_msg = await update.message.reply_text(
        f"📤 পাঠানো হচ্ছে {len(user_ids)} জনকে..."
    )

    for uid in user_ids:
        try:
            await context.bot.send_message(
                chat_id    = uid,
                text       = f"📢 *PickDeal BD ঘোষণা:*\n\n{message_text}",
                parse_mode = "Markdown",
            )
            sent += 1
        except Exception:
            failed += 1

    await status_msg.edit_text(
        f"✅ *ব্রডকাস্ট সম্পন্ন!*\n\n"
        f"✔️ পাঠানো হয়েছে: {sent}\n"
        f"❌ ব্যর্থ: {failed}",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


# ─── Analytics ───────────────────────────────────────────────────────────────

async def analytics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    st = order_model.stats()
    by = st["by_status"]

    # Top products by sold_count
    from database.connection import get_conn
    top = get_conn().execute(
        "SELECT name, sold_count FROM products ORDER BY sold_count DESC LIMIT 5"
    ).fetchall()
    top_lines = "\n".join(
        f"  {i+1}. {r['name']} ({r['sold_count']} বিক্রি)"
        for i, r in enumerate(top)
    ) or "  _ডেটা নেই_"

    text = (
        f"📊 *অ্যানালিটিক্স ড্যাশবোর্ড*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 মোট ব্যবহারকারী: {user_model.count()}\n"
        f"📦 মোট অর্ডার:      {st['total']}\n"
        f"💰 মোট রাজস্ব:      {taka(st['revenue'])}\n"
        f"📅 আজকের অর্ডার:   {st['today']}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🕐 Pending:          {by.get('pending', 0)}\n"
        f"✅ Confirmed:         {by.get('payment_confirmed', 0)}\n"
        f"⚙️  Processing:       {by.get('processing', 0)}\n"
        f"📦 Packed:           {by.get('packed', 0)}\n"
        f"🚚 Shipping:         {by.get('shipping', 0)}\n"
        f"🛵 Out for delivery: {by.get('out_for_delivery', 0)}\n"
        f"🎉 Delivered:        {by.get('delivered', 0)}\n"
        f"❌ Cancelled:         {by.get('cancelled', 0)}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 *সেরা পণ্য সমূহ:*\n{top_lines}"
    )

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("⬅️ Dashboard", callback_data="adm_dashboard")
        ]])
    )


# ─── Coupon Management ────────────────────────────────────────────────────────

async def coupons_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    coupons = coupon_model.get_all()
    if not coupons:
        lines = "_কোনো কুপন নেই।_"
    else:
        lines = "\n".join(
            f"• `{c['code']}` — {c['value']}{'%' if c['type']=='percent' else '৳'} "
            f"({'✅' if c['is_active'] else '❌'}) "
            f"[{c['used_count']}/{c['max_uses']}]"
            for c in coupons
        )

    await query.edit_message_text(
        f"🎫 *কুপন লিস্ট*\n\n{lines}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ নতুন কুপন", callback_data="adm_add_coupon")],
            [InlineKeyboardButton("⬅️ Dashboard",  callback_data="adm_dashboard")],
        ])
    )


async def start_add_coupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "🎫 *নতুন কুপন যোগ করুন*\n\n"
        "এই ফরম্যাটে লিখুন:\n"
        "`CODE টাইপ মান মিনিমাম_অর্ডার সর্বোচ্চ_ব্যবহার`\n\n"
        "টাইপ: `percent` বা `fixed`\n\n"
        "*উদাহরণ:*\n"
        "`SAVE15 percent 15 500 200`\n"
        "_(১৫% ছাড়, সর্বনিম্ন ৫০০ টাকা, ২০০ বার)_",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ বাতিল", callback_data="adm_coupons")
        ]])
    )
    return COUPON_INPUT


async def save_coupon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END

    try:
        parts   = update.message.text.strip().split()
        code    = parts[0].upper()
        typ     = parts[1]
        value   = float(parts[2])
        min_ord = float(parts[3]) if len(parts) > 3 else 0
        max_use = int(parts[4])   if len(parts) > 4 else 100

        from database.connection import get_conn
        conn = get_conn()
        conn.execute(
            "INSERT OR REPLACE INTO coupons(code,type,value,min_order,max_uses) VALUES(?,?,?,?,?)",
            (code, typ, value, min_ord, max_use)
        )
        conn.commit()

        await update.message.reply_text(
            f"✅ কুপন `{code}` তৈরি হয়েছে!",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🎫 কুপন লিস্ট", callback_data="adm_coupons")
            ]])
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ ত্রুটি: {e}\n\nআবার চেষ্টা করুন।"
        )

    return ConversationHandler.END


async def cancel_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text("❌ বাতিল।")
    return ConversationHandler.END
