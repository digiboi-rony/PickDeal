"""
main.py
=======
PickDeal BD — Production-ready Telegram E-Commerce Bot
Entry point: registers all handlers, conversation flows, and starts polling.

Deployment: Railway / Termux / Local
"""

import logging
import os
import sys

# ─── Make sure project root is on path ───────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from config.settings import setup_logging, BOT_TOKEN
setup_logging()
logger = logging.getLogger(__name__)

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)

from database.db_setup import initialize_database

# ── User Handlers ─────────────────────────────────────────────────
from handlers.start_handler import (
    start, main_menu, my_profile, my_wishlist, toggle_wishlist,
    recently_viewed, search_prompt, handle_search,
    customer_support, noop, SEARCH_STATE,
)
from handlers.product_handler import (
    show_categories, show_products, show_product_detail,
    show_featured_products, show_bestsellers,
    add_to_cart_handler, view_cart, cart_quantity_handler,
    cart_delete_handler, clear_cart_handler, share_product,
)
from handlers.order_handler import (
    start_order, checkout_from_cart, get_area, get_name, get_phone,
    get_address, get_notes, confirm_order, cancel_order,
    use_coupon_prompt, apply_coupon,
    AREA, NAME, PHONE, ADDRESS, NOTES, CONFIRM, COUPON_STATE,
)
from handlers.payment_handler import (
    select_payment_method, show_payment_instructions,
    receive_payment_screenshot, WAITING_SCREENSHOT,
)
from handlers.tracking_handler import (
    my_orders, view_order_detail, track_order,
)
from handlers.support_handler import (
    new_ticket_prompt, receive_ticket, my_tickets, TICKET_MESSAGE,
)

# ── Admin Handlers ────────────────────────────────────────────────
from admin.admin_handler import (
    admin_panel,
    admin_view_orders, admin_view_order_detail, admin_update_order,
    admin_search_prompt, admin_search_order_text,
    admin_list_products, admin_view_product,
    admin_add_product_start, add_prod_name, add_prod_cat, add_prod_desc,
    add_prod_price, add_prod_disc, add_prod_stock, add_prod_image,
    admin_edit_product_field, admin_save_product_edit,
    admin_analytics, admin_customers,
    admin_broadcast_prompt, admin_send_broadcast,
    admin_coupons, admin_add_coupon_start,
    add_coupon_code, add_coupon_disc, add_coupon_min,
    admin_low_stock,
    admin_view_tickets, admin_view_ticket_detail,
    admin_reply_ticket_prompt, admin_send_ticket_reply, admin_close_ticket,
    BROADCAST_MSG,
    ADD_PROD_NAME, ADD_PROD_CAT, ADD_PROD_DESC,
    ADD_PROD_PRICE, ADD_PROD_DISC, ADD_PROD_STOCK, ADD_PROD_IMAGE,
    EDIT_PROD_VAL,
    ADD_COUPON_CODE, ADD_COUPON_DISC, ADD_COUPON_MIN,
    TICKET_REPLY,
)


# ═══════════════════════════════════════════════════════════════════
# ERROR HANDLER
# ═══════════════════════════════════════════════════════════════════

async def error_handler(update: object, context) -> None:
    logger.error("Exception while handling an update:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "⚠️ একটি সমস্যা হয়েছে। অনুগ্রহ করে /start দিয়ে আবার চেষ্টা করুন।"
            )
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════
# CONVERSATION HANDLERS
# ═══════════════════════════════════════════════════════════════════

def build_order_conversation() -> ConversationHandler:
    """
    Checkout flow: triggered by Buy Now or Checkout button.
    Handles: Area → Name → Phone → Address → Notes → Confirm
    """
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_order,         pattern=r"^order_\d+$"),
            CallbackQueryHandler(checkout_from_cart,  pattern=r"^checkout$"),
        ],
        states={
            AREA:    [CallbackQueryHandler(get_area,  pattern=r"^area_(inside|outside)$")],
            NAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            NOTES:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_notes)],
            CONFIRM: [CallbackQueryHandler(confirm_order, pattern=r"^(confirm_order|cancel_order)$")],
        },
        fallbacks=[
            CallbackQueryHandler(cancel_order, pattern=r"^cancel_order$"),
            CommandHandler("start", start),
        ],
        allow_reentry=True,
        name="order_conversation",
        persistent=False,
    )


def build_payment_conversation() -> ConversationHandler:
    """
    Payment flow: triggered by Pay Now button.
    Handles: Method Selection → Instructions → Screenshot Upload
    """
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(show_payment_instructions, pattern=r"^pay_\d+_(bkash|nagad|cod)$"),
        ],
        states={
            WAITING_SCREENSHOT: [
                MessageHandler(filters.PHOTO, receive_payment_screenshot),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(my_orders, pattern=r"^my_orders$"),
            CommandHandler("start", start),
        ],
        allow_reentry=True,
        name="payment_conversation",
    )


def build_search_conversation() -> ConversationHandler:
    """Search flow: prompt → receive text → show results."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(search_prompt, pattern=r"^search_products$"),
        ],
        states={
            SEARCH_STATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(main_menu, pattern=r"^main_menu$"),
            CommandHandler("start", start),
        ],
        allow_reentry=True,
        name="search_conversation",
    )


def build_coupon_conversation() -> ConversationHandler:
    """Coupon flow: prompt → receive code → apply."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(use_coupon_prompt, pattern=r"^use_coupon$"),
        ],
        states={
            COUPON_STATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, apply_coupon),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(main_menu, pattern=r"^main_menu$"),
            CommandHandler("start", start),
        ],
        allow_reentry=True,
        name="coupon_conversation",
    )


def build_support_conversation() -> ConversationHandler:
    """Support ticket flow: prompt → receive message → save."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(new_ticket_prompt, pattern=r"^new_ticket$"),
        ],
        states={
            TICKET_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_ticket),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(customer_support, pattern=r"^support$"),
            CommandHandler("start", start),
        ],
        allow_reentry=True,
        name="support_conversation",
    )


def build_admin_conversations() -> list[ConversationHandler]:
    """All admin multi-step flows."""

    # ── Broadcast ─────────────────────────────────────────────────
    broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_broadcast_prompt, pattern=r"^admin_broadcast$")],
        states={
            BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_send_broadcast)],
        },
        fallbacks=[
            CallbackQueryHandler(admin_panel, pattern=r"^admin_panel$"),
            CommandHandler("start", start),
        ],
        allow_reentry=True,
        name="broadcast_conversation",
    )

    # ── Add Product ───────────────────────────────────────────────
    add_product_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_add_product_start, pattern=r"^admin_add_product$")],
        states={
            ADD_PROD_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, add_prod_name)],
            ADD_PROD_CAT:   [MessageHandler(filters.TEXT & ~filters.COMMAND, add_prod_cat)],
            ADD_PROD_DESC:  [MessageHandler(filters.TEXT & ~filters.COMMAND, add_prod_desc)],
            ADD_PROD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_prod_price)],
            ADD_PROD_DISC:  [MessageHandler(filters.TEXT & ~filters.COMMAND, add_prod_disc)],
            ADD_PROD_STOCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_prod_stock)],
            ADD_PROD_IMAGE: [
                MessageHandler(filters.PHOTO, add_prod_image),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_prod_image),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(admin_panel, pattern=r"^admin_panel$"),
            CommandHandler("start", start),
        ],
        allow_reentry=True,
        name="add_product_conversation",
    )

    # ── Edit Product ──────────────────────────────────────────────
    edit_product_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_edit_product_field, pattern=r"^admprod_(name|price|discount|stock|image|featured|delete)_\d+$"),
        ],
        states={
            EDIT_PROD_VAL: [
                MessageHandler(filters.PHOTO, admin_save_product_edit),
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_save_product_edit),
            ],
        },
        fallbacks=[
            CallbackQueryHandler(admin_panel, pattern=r"^admin_panel$"),
            CommandHandler("start", start),
        ],
        allow_reentry=True,
        name="edit_product_conversation",
    )

    # ── Add Coupon ────────────────────────────────────────────────
    add_coupon_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_add_coupon_start, pattern=r"^admin_add_coupon$")],
        states={
            ADD_COUPON_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_coupon_code)],
            ADD_COUPON_DISC: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_coupon_disc)],
            ADD_COUPON_MIN:  [MessageHandler(filters.TEXT & ~filters.COMMAND, add_coupon_min)],
        },
        fallbacks=[
            CallbackQueryHandler(admin_panel, pattern=r"^admin_panel$"),
            CommandHandler("start", start),
        ],
        allow_reentry=True,
        name="add_coupon_conversation",
    )

    # ── Ticket Reply ──────────────────────────────────────────────
    ticket_reply_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_reply_ticket_prompt, pattern=r"^admticket_reply_\d+$"),
        ],
        states={
            TICKET_REPLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_send_ticket_reply)],
        },
        fallbacks=[
            CallbackQueryHandler(admin_view_tickets, pattern=r"^admin_tickets$"),
            CommandHandler("start", start),
        ],
        allow_reentry=True,
        name="ticket_reply_conversation",
    )

    return [broadcast_conv, add_product_conv, edit_product_conv, add_coupon_conv, ticket_reply_conv]


# ═══════════════════════════════════════════════════════════════════
# MAIN APPLICATION BUILDER
# ═══════════════════════════════════════════════════════════════════

def build_application() -> Application:
    if not BOT_TOKEN:
        logger.critical("❌ BOT_TOKEN not set! Set it in .env or environment variables.")
        sys.exit(1)

    app = Application.builder().token(BOT_TOKEN).build()

    # ── 1. Conversation handlers (must be registered FIRST) ───────
    app.add_handler(build_order_conversation())
    app.add_handler(build_payment_conversation())
    app.add_handler(build_search_conversation())
    app.add_handler(build_coupon_conversation())
    app.add_handler(build_support_conversation())
    for conv in build_admin_conversations():
        app.add_handler(conv)

    # ── 2. Command handlers ───────────────────────────────────────
    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("menu",   start))
    app.add_handler(CommandHandler("orders", my_orders))
    app.add_handler(CommandHandler("cart",   view_cart))
    app.add_handler(CommandHandler("track",  track_order))
    app.add_handler(CommandHandler("admin",  admin_panel))

    # ── 3. Admin callback handlers ────────────────────────────────
    app.add_handler(CallbackQueryHandler(admin_panel,           pattern=r"^admin_panel$"))
    app.add_handler(CallbackQueryHandler(admin_view_orders,     pattern=r"^admin_orders_\w+_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_view_order_detail, pattern=r"^admview_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_update_order,    pattern=r"^admupd_\d+_\w+$"))
    app.add_handler(CallbackQueryHandler(admin_search_prompt,   pattern=r"^admin_search$"))
    app.add_handler(CallbackQueryHandler(admin_list_products,   pattern=r"^admin_list_products_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_view_product,    pattern=r"^admview_prod_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_analytics,       pattern=r"^admin_analytics$"))
    app.add_handler(CallbackQueryHandler(admin_customers,       pattern=r"^admin_customers$"))
    app.add_handler(CallbackQueryHandler(admin_coupons,         pattern=r"^admin_coupons$"))
    app.add_handler(CallbackQueryHandler(admin_low_stock,       pattern=r"^admin_low_stock$"))
    app.add_handler(CallbackQueryHandler(admin_view_tickets,    pattern=r"^admin_tickets$"))
    app.add_handler(CallbackQueryHandler(admin_view_ticket_detail, pattern=r"^admticket_view_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_close_ticket,    pattern=r"^admticket_close_\d+$"))

    # ── 4. User navigation callback handlers ──────────────────────
    app.add_handler(CallbackQueryHandler(main_menu,             pattern=r"^main_menu$"))
    app.add_handler(CallbackQueryHandler(show_categories,       pattern=r"^browse_products$"))
    app.add_handler(CallbackQueryHandler(show_featured_products,pattern=r"^featured_products$"))
    app.add_handler(CallbackQueryHandler(show_bestsellers,      pattern=r"^bestseller_products$"))
    app.add_handler(CallbackQueryHandler(show_products,         pattern=r"^cat_[^_]+(_p\d+)?$"))
    app.add_handler(CallbackQueryHandler(show_product_detail,   pattern=r"^product_\d+$"))

    # ── 5. Cart callback handlers ─────────────────────────────────
    app.add_handler(CallbackQueryHandler(add_to_cart_handler,   pattern=r"^addcart_\d+$"))
    app.add_handler(CallbackQueryHandler(view_cart,             pattern=r"^view_cart$"))
    app.add_handler(CallbackQueryHandler(cart_quantity_handler, pattern=r"^cartqty_\d+_(inc|dec)$"))
    app.add_handler(CallbackQueryHandler(cart_delete_handler,   pattern=r"^cartdel_\d+$"))
    app.add_handler(CallbackQueryHandler(clear_cart_handler,    pattern=r"^clear_cart$"))
    app.add_handler(CallbackQueryHandler(share_product,         pattern=r"^share_\d+$"))

    # ── 6. Payment flow callbacks ─────────────────────────────────
    app.add_handler(CallbackQueryHandler(select_payment_method, pattern=r"^payorder_\d+$"))

    # ── 7. Order tracking callbacks ───────────────────────────────
    app.add_handler(CallbackQueryHandler(my_orders,             pattern=r"^my_orders$"))
    app.add_handler(CallbackQueryHandler(view_order_detail,     pattern=r"^vieworder_\d+$"))
    app.add_handler(CallbackQueryHandler(track_order,           pattern=r"^track_order$"))

    # ── 8. User profile & wishlist callbacks ──────────────────────
    app.add_handler(CallbackQueryHandler(my_profile,            pattern=r"^my_profile$"))
    app.add_handler(CallbackQueryHandler(my_wishlist,           pattern=r"^my_wishlist$"))
    app.add_handler(CallbackQueryHandler(toggle_wishlist,       pattern=r"^wish_\d+$"))
    app.add_handler(CallbackQueryHandler(recently_viewed,       pattern=r"^recently_viewed$"))

    # ── 9. Support callbacks ──────────────────────────────────────
    app.add_handler(CallbackQueryHandler(customer_support,      pattern=r"^support$"))
    app.add_handler(CallbackQueryHandler(my_tickets,            pattern=r"^my_tickets$"))

    # ── 10. Misc ──────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(noop,                  pattern=r"^noop$"))

    # ── 11. Admin text search (message fallback) ──────────────────
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        admin_search_order_text
    ))

    # ── 12. Global error handler ──────────────────────────────────
    app.add_error_handler(error_handler)

    return app


# ═══════════════════════════════════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════════════════════════════════

def main():
    logger.info("🚀 PickDeal BD Bot starting...")
    initialize_database()
    logger.info("✅ Database ready.")

    app = build_application()
    logger.info("✅ All handlers registered. Starting polling...")

    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
