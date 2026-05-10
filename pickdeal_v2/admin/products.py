"""admin/products.py — add, edit, delete, image upload for products"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

import models.product as pm
from keyboards.admin_kb import product_list_kb, product_action_kb
from middlewares.auth import is_admin
from utils.formatters import product_card

logger = logging.getLogger(__name__)

# ConversationHandler states for adding a product
(AP_NAME, AP_DESC, AP_PRICE, AP_DISC, AP_STOCK, AP_CAT, AP_IMG) = range(400, 407)
# ConversationHandler states for editing a field
(EP_VALUE,) = range(410, 411)


async def list_products(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """adm_products_<page>"""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    page     = int(query.data.split("_")[2]) if "_" in query.data else 0
    products = pm.get_all_for_admin(page)

    await query.edit_message_text(
        f"📦 *পণ্য ম্যানেজমেন্ট* (পৃষ্ঠা {page+1})\n\nপণ্য বেছে নিন:",
        parse_mode="Markdown",
        reply_markup=product_list_kb(products, page),
    )


async def product_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """adm_product_<product_id>"""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    product_id = int(query.data.split("_")[2])
    p          = pm.get(product_id)
    if not p:
        await query.answer("পণ্য পাওয়া যায়নি!", show_alert=True)
        return

    await query.edit_message_text(
        f"🛠️ *পণ্য বিবরণ*\n\n{product_card(p)}\n\n📦 স্টক: {p['stock']}",
        parse_mode="Markdown",
        reply_markup=product_action_kb(product_id),
    )


async def toggle_featured(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """adm_pfeat_<product_id>"""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    product_id = int(query.data.split("_")[2])
    p          = pm.get(product_id)
    new_val    = 0 if p["is_featured"] else 1
    pm.update_field(product_id, "is_featured", new_val)
    label = "⭐ Featured করা হয়েছে!" if new_val else "Featured সরানো হয়েছে।"
    await query.answer(label)

    # Refresh
    p = pm.get(product_id)
    await query.edit_message_text(
        f"🛠️ *পণ্য বিবরণ*\n\n{product_card(p)}\n\n📦 স্টক: {p['stock']}",
        parse_mode="Markdown",
        reply_markup=product_action_kb(product_id),
    )


async def delete_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """adm_pdel_<product_id>"""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    product_id = int(query.data.split("_")[2])
    pm.delete(product_id)
    await query.edit_message_text(
        "🗑️ পণ্যটি মুছে ফেলা হয়েছে (deactivated)।",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📦 পণ্য লিস্ট", callback_data="adm_products_0")
        ]])
    )


# ─── Add Product Conversation ─────────────────────────────────────────────────

async def start_add_product(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """adm_add_product callback"""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    context.user_data["new_product"] = {}
    await query.edit_message_text(
        "➕ *নতুন পণ্য যোগ করুন*\n\n*ধাপ ১/৬ — পণ্যের নাম লিখুন:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ বাতিল", callback_data="adm_products_0")
        ]])
    )
    return AP_NAME


async def ap_get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_product"]["name"] = update.message.text.strip()
    await update.message.reply_text(
        "*ধাপ ২/৬ — পণ্যের বিবরণ লিখুন:*\n_(বৈশিষ্ট্য, সুবিধা ইত্যাদি)_",
        parse_mode="Markdown"
    )
    return AP_DESC


async def ap_get_desc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_product"]["description"] = update.message.text.strip()
    await update.message.reply_text(
        "*ধাপ ৩/৬ — মূল মূল্য লিখুন:* (শুধু সংখ্যা, যেমন: 1299)",
        parse_mode="Markdown"
    )
    return AP_PRICE


async def ap_get_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        price = float(update.message.text.strip())
        context.user_data["new_product"]["price"] = price
        await update.message.reply_text(
            "*ধাপ ৪/৬ — ডিসকাউন্ট মূল্য লিখুন:*\n_(না থাকলে 0 লিখুন)_",
            parse_mode="Markdown"
        )
        return AP_DISC
    except ValueError:
        await update.message.reply_text("⚠️ শুধু সংখ্যা লিখুন, যেমন: 1299")
        return AP_PRICE


async def ap_get_disc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        disc = float(update.message.text.strip())
        context.user_data["new_product"]["discount_price"] = disc if disc > 0 else None
        await update.message.reply_text(
            "*ধাপ ৫/৬ — স্টক পরিমাণ লিখুন:* (যেমন: 50)",
            parse_mode="Markdown"
        )
        return AP_STOCK
    except ValueError:
        await update.message.reply_text("⚠️ শুধু সংখ্যা লিখুন।")
        return AP_DISC


async def ap_get_stock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data["new_product"]["stock"] = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("⚠️ পূর্ণসংখ্যা লিখুন।")
        return AP_STOCK

    cats = pm.get_categories()
    buttons = [
        [InlineKeyboardButton(f"{c['emoji']} {c['name']}", callback_data=f"apc_{c['cat_id']}")]
        for c in cats
    ]
    await update.message.reply_text(
        "*ধাপ ৬/৬ — ক্যাটাগরি বেছে নিন:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    return AP_CAT


async def ap_get_cat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    cat_id = int(query.data.split("_")[1])
    np     = context.user_data["new_product"]

    product_id = pm.create(
        cat_id     = cat_id,
        name       = np["name"],
        desc       = np["description"],
        price      = np["price"],
        disc_price = np.get("discount_price"),
        stock      = np["stock"],
    )
    context.user_data["new_product"]["product_id"] = product_id
    context.user_data.pop("new_product", None)

    await query.edit_message_text(
        f"✅ *পণ্য তৈরি হয়েছে! ID: #{product_id}*\n\n"
        "পণ্যের ছবি পাঠান (optional):\n"
        "_(ছবি ছাড়া সংরক্ষণ করতে 'skip' লিখুন)_",
        parse_mode="Markdown",
    )
    context.user_data["img_product_id"] = product_id
    return AP_IMG


async def ap_get_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    product_id = context.user_data.get("img_product_id")
    if not product_id:
        return ConversationHandler.END

    if update.message.photo:
        file_id = update.message.photo[-1].file_id
        pm.add_image(product_id, file_id)
        await update.message.reply_text("✅ ছবি যোগ হয়েছে!")
    elif update.message.text and update.message.text.lower() == "skip":
        pass

    context.user_data.pop("img_product_id", None)
    await update.message.reply_text(
        "✅ পণ্য সম্পূর্ণভাবে যোগ হয়েছে!",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("📦 পণ্য লিস্ট", callback_data="adm_products_0"),
            InlineKeyboardButton("⬅️ Dashboard",  callback_data="adm_dashboard"),
        ]])
    )
    return ConversationHandler.END


# ─── Edit Product Field ───────────────────────────────────────────────────────

async def start_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """adm_pedit_<product_id>_<field>"""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    parts      = query.data.split("_")
    product_id = int(parts[2])
    field      = parts[3]

    field_labels = {
        "name":           "নাম",
        "price":          "মূল্য (সংখ্যা)",
        "discount_price": "ডিসকাউন্ট মূল্য (0 = সরান)",
        "stock":          "স্টক পরিমাণ",
    }
    context.user_data["edit_field"]      = field
    context.user_data["edit_product_id"] = product_id

    await query.edit_message_text(
        f"✏️ *{field_labels.get(field, field)} পরিবর্তন করুন:*\n\nনতুন মান লিখুন:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ বাতিল", callback_data=f"adm_product_{product_id}")
        ]])
    )
    return EP_VALUE


async def save_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    field      = context.user_data.get("edit_field")
    product_id = context.user_data.get("edit_product_id")
    raw        = update.message.text.strip()

    try:
        if field in ("price", "discount_price"):
            value = float(raw)
            if field == "discount_price" and value == 0:
                value = None
        elif field == "stock":
            value = int(raw)
        else:
            value = raw

        pm.update_field(product_id, field, value)
        await update.message.reply_text(
            f"✅ আপডেট হয়েছে!",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("📦 পণ্য দেখুন", callback_data=f"adm_product_{product_id}")
            ]])
        )
    except Exception as e:
        await update.message.reply_text(f"❌ ত্রুটি: {e}")

    context.user_data.pop("edit_field", None)
    context.user_data.pop("edit_product_id", None)
    return ConversationHandler.END


# ─── Add Image to existing product ───────────────────────────────────────────

async def start_add_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """adm_pimg_<product_id>"""
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return

    product_id = int(query.data.split("_")[2])
    context.user_data["img_product_id"] = product_id

    await query.edit_message_text(
        "🖼️ পণ্যের ছবি পাঠান:",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ বাতিল", callback_data=f"adm_product_{product_id}")
        ]])
    )
    return AP_IMG


async def cancel_admin_conv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("new_product", None)
    context.user_data.pop("edit_field", None)
    context.user_data.pop("edit_product_id", None)
    if update.message:
        await update.message.reply_text("❌ বাতিল।")
    return ConversationHandler.END
