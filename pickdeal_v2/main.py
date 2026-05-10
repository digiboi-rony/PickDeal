"""
main.py — PickDeal BD v2 Bot Entry Point
=========================================
Registers ALL handlers and starts the bot.
"""
import logging
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters,
)
from config.settings import BOT_TOKEN, setup_logging
from database.schema import initialize
from database.seed   import run as seed

# Handlers
from handlers.start    import start, main_menu_handler
from handlers.products import (
    browse, show_category, show_product,
    add_to_cart, buy_now, toggle_wishlist,
    show_featured, search_prompt, do_search, SEARCHING,
)
from handlers.cart     import (
    view_cart, qty_increase, qty_decrease, remove_item, clear_cart
)
from handlers.checkout import (
    start_checkout, get_name, get_phone, get_address,
    get_area, get_notes, skip_coupon, apply_coupon_input,
    confirm_order_handler, cancel_checkout,
    NAME, PHONE, ADDRESS, AREA, NOTES, COUPON_WAIT, REVIEW,
)
from handlers.payment  import choose_payment, receive_screenshot, WAITING_SCREENSHOT
from handlers.tracking import my_orders, order_detail, track_cmd
from handlers.profile  import profile, wishlist
from handlers.support  import (
    support_menu, faq_payment, faq_return,
    start_ticket, save_ticket, TICKET_MSG,
)

# Admin
from admin.dashboard import dashboard
from admin.orders    import list_orders, order_detail as adm_order_detail, update_status
from admin.products  import (
    list_products, product_detail as adm_product_detail,
    toggle_featured, delete_product,
    start_add_product, ap_get_name, ap_get_desc, ap_get_price,
    ap_get_disc, ap_get_stock, ap_get_cat, ap_get_image,
    start_edit_field, save_edit_field,
    start_add_image, cancel_admin_conv,
    AP_NAME, AP_DESC, AP_PRICE, AP_DISC, AP_STOCK, AP_CAT, AP_IMG, EP_VALUE,
)
from admin.broadcast import (
    start_broadcast, send_broadcast,
    analytics, coupons_list,
    start_add_coupon, save_coupon, cancel_admin,
    BROADCAST_TEXT, COUPON_INPUT,
)

logger = logging.getLogger(__name__)


def main():
    setup_logging()
    logger.info("🚀 Starting PickDeal BD v2...")

    # Initialize DB
    initialize()
    seed()
    logger.info("✅ Database ready.")

    app = Application.builder().token(BOT_TOKEN).build()

    # ─── Checkout ConversationHandler ─────────────────────────────────────────
    checkout_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_checkout, pattern="^checkout$")],
        states={
            NAME:        [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE:       [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            ADDRESS:     [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            AREA:        [CallbackQueryHandler(get_area, pattern="^area_")],
            NOTES:       [MessageHandler(filters.TEXT & ~filters.COMMAND, get_notes)],
            COUPON_WAIT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, apply_coupon_input),
                CallbackQueryHandler(skip_coupon, pattern="^skip_coupon$"),
            ],
            REVIEW: [
                CallbackQueryHandler(confirm_order_handler, pattern="^confirm_order$"),
                CallbackQueryHandler(cancel_checkout,       pattern="^main_menu$"),
            ],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_checkout),
            CallbackQueryHandler(cancel_checkout, pattern="^main_menu$"),
        ],
        allow_reentry=True,
    )

    # ─── Payment Screenshot ConversationHandler ────────────────────────────────
    payment_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(choose_payment, pattern="^pay_\\d+_")],
        states={
            WAITING_SCREENSHOT: [MessageHandler(filters.PHOTO, receive_screenshot)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_checkout),
            CallbackQueryHandler(cancel_checkout, pattern="^main_menu$"),
        ],
        allow_reentry=True,
    )

    # ─── Search ConversationHandler ────────────────────────────────────────────
    search_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(search_prompt, pattern="^search_prompt$")],
        states={
            SEARCHING: [MessageHandler(filters.TEXT & ~filters.COMMAND, do_search)],
        },
        fallbacks=[CallbackQueryHandler(cancel_checkout, pattern="^main_menu$")],
        allow_reentry=True,
    )

    # ─── Support Ticket ConversationHandler ───────────────────────────────────
    support_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_ticket, pattern="^send_ticket$")],
        states={
            TICKET_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_ticket)],
        },
        fallbacks=[CallbackQueryHandler(cancel_checkout, pattern="^main_menu$")],
        allow_reentry=True,
    )

    # ─── Admin Add Product ConversationHandler ────────────────────────────────
    add_product_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add_product, pattern="^adm_add_product$")],
        states={
            AP_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, ap_get_name)],
            AP_DESC:  [MessageHandler(filters.TEXT & ~filters.COMMAND, ap_get_desc)],
            AP_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ap_get_price)],
            AP_DISC:  [MessageHandler(filters.TEXT & ~filters.COMMAND, ap_get_disc)],
            AP_STOCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, ap_get_stock)],
            AP_CAT:   [CallbackQueryHandler(ap_get_cat, pattern="^apc_")],
            AP_IMG:   [
                MessageHandler(filters.PHOTO, ap_get_image),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ap_get_image),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_admin_conv)],
        allow_reentry=True,
    )

    # ─── Admin Add Image ConversationHandler ──────────────────────────────────
    add_img_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add_image, pattern="^adm_pimg_")],
        states={
            AP_IMG: [
                MessageHandler(filters.PHOTO, ap_get_image),
                MessageHandler(filters.TEXT & ~filters.COMMAND, ap_get_image),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_admin_conv)],
        allow_reentry=True,
    )

    # ─── Admin Edit Field ConversationHandler ─────────────────────────────────
    edit_field_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_edit_field, pattern="^adm_pedit_")],
        states={
            EP_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_edit_field)],
        },
        fallbacks=[CommandHandler("cancel", cancel_admin_conv)],
        allow_reentry=True,
    )

    # ─── Admin Broadcast ConversationHandler ──────────────────────────────────
    broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_broadcast, pattern="^adm_broadcast$")],
        states={
            BROADCAST_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_broadcast)],
        },
        fallbacks=[CommandHandler("cancel", cancel_admin)],
        allow_reentry=True,
    )

    # ─── Admin Coupon ConversationHandler ─────────────────────────────────────
    coupon_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_add_coupon, pattern="^adm_add_coupon$")],
        states={
            COUPON_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_coupon)],
        },
        fallbacks=[CommandHandler("cancel", cancel_admin)],
        allow_reentry=True,
    )

    # ═══ Register all handlers ════════════════════════════════════════════════

    # Commands
    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("admin",  dashboard))
    app.add_handler(CommandHandler("orders", my_orders))
    app.add_handler(CommandHandler("track",  track_cmd))

    # Conversations (MUST come before generic callback handlers)
    app.add_handler(checkout_conv)
    app.add_handler(payment_conv)
    app.add_handler(search_conv)
    app.add_handler(support_conv)
    app.add_handler(add_product_conv)
    app.add_handler(add_img_conv)
    app.add_handler(edit_field_conv)
    app.add_handler(broadcast_conv)
    app.add_handler(coupon_conv)

    # ─── User callbacks ───────────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(main_menu_handler, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(browse,            pattern="^browse$"))
    app.add_handler(CallbackQueryHandler(show_featured,     pattern="^featured$"))
    app.add_handler(CallbackQueryHandler(show_category,     pattern="^cat_\\d+"))
    app.add_handler(CallbackQueryHandler(show_product,      pattern="^product_\\d+$"))
    app.add_handler(CallbackQueryHandler(add_to_cart,       pattern="^addcart_"))
    app.add_handler(CallbackQueryHandler(buy_now,           pattern="^buynow_"))
    app.add_handler(CallbackQueryHandler(toggle_wishlist,   pattern="^wish_"))
    app.add_handler(CallbackQueryHandler(view_cart,         pattern="^view_cart$"))
    app.add_handler(CallbackQueryHandler(qty_increase,      pattern="^qty_inc_"))
    app.add_handler(CallbackQueryHandler(qty_decrease,      pattern="^qty_dec_"))
    app.add_handler(CallbackQueryHandler(remove_item,       pattern="^remove_"))
    app.add_handler(CallbackQueryHandler(clear_cart,        pattern="^clear_cart$"))
    app.add_handler(CallbackQueryHandler(my_orders,         pattern="^my_orders$"))
    app.add_handler(CallbackQueryHandler(order_detail,      pattern="^order_detail_"))
    app.add_handler(CallbackQueryHandler(choose_payment,    pattern="^choose_payment_"))
    app.add_handler(CallbackQueryHandler(profile,           pattern="^profile$"))
    app.add_handler(CallbackQueryHandler(wishlist,          pattern="^my_wishlist$"))
    app.add_handler(CallbackQueryHandler(support_menu,      pattern="^support$"))
    app.add_handler(CallbackQueryHandler(faq_payment,       pattern="^faq_payment$"))
    app.add_handler(CallbackQueryHandler(faq_return,        pattern="^faq_return$"))

    # ─── Admin callbacks ──────────────────────────────────────────────────────
    app.add_handler(CallbackQueryHandler(dashboard,           pattern="^adm_dashboard$"))
    app.add_handler(CallbackQueryHandler(list_orders,         pattern="^adm_orders_"))
    app.add_handler(CallbackQueryHandler(adm_order_detail,    pattern="^adm_order_\\d+$"))
    app.add_handler(CallbackQueryHandler(update_status,       pattern="^adm_upd_"))
    app.add_handler(CallbackQueryHandler(list_products,       pattern="^adm_products_\\d+$"))
    app.add_handler(CallbackQueryHandler(adm_product_detail,  pattern="^adm_product_\\d+$"))
    app.add_handler(CallbackQueryHandler(toggle_featured,     pattern="^adm_pfeat_"))
    app.add_handler(CallbackQueryHandler(delete_product,      pattern="^adm_pdel_"))
    app.add_handler(CallbackQueryHandler(analytics,           pattern="^adm_analytics$"))
    app.add_handler(CallbackQueryHandler(coupons_list,        pattern="^adm_coupons$"))

    # Noop (pagination label buttons)
    app.add_handler(CallbackQueryHandler(lambda u, c: u.callback_query.answer(),
                                          pattern="^noop$"))

    logger.info("✅ All handlers registered.")
    logger.info("🤖 Bot is polling. Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
