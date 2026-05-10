"""
main.py — PickDeal BD v3.1 FIXED
"""
import logging, os, sys, traceback
sys.path.insert(0, os.path.dirname(__file__))

from config.settings import setup_logging, BOT_TOKEN
setup_logging()
logger = logging.getLogger(__name__)

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters,
)
from database.db_setup import initialize_database

from handlers.start_handler import (
    start, main_menu, my_profile, my_wishlist, toggle_wishlist,
    recently_viewed_handler, search_prompt, handle_search_input,
    customer_support, my_tickets, noop, SEARCH_INPUT,
)
from handlers.product_handler import (
    show_categories, show_products_by_catid, show_product_detail,
    show_featured_products, show_bestsellers, show_new_arrivals,
    add_to_cart_handler, view_cart, cart_qty_handler,
    cart_del_handler, clear_cart_handler, share_product,
)
from handlers.order_handler import (
    buy_now, checkout_from_cart, get_delivery, get_name, get_phone,
    get_address, get_notes, confirm_order, cancel_checkout,
    coupon_prompt, apply_coupon,
    DELIVERY, NAME, PHONE, ADDRESS, NOTES, CONFIRM, COUPON_INPUT,
)
from handlers.payment_handler import (
    select_payment, show_payment_instructions, receive_screenshot, WAITING_SCREENSHOT,
)
from handlers.tracking_handler import (
    my_orders, view_order_detail, track_order,
    new_ticket_prompt, receive_ticket, TICKET_MSG,
)
from handlers.review_handler import (
    review_prompt, handle_star_rating, handle_review_note, REVIEW_NOTE,
)
from admin.admin_handler import (
    admin_panel, admin_view_orders, admin_view_order_detail, admin_update_order,
    admin_order_note_prompt, admin_order_note_save,
    admin_list_products, admin_view_product,
    admin_add_product_start, _ap_name, _ap_cat, _ap_desc, _ap_price, _ap_disc, _ap_stock, _ap_image,
    admin_edit_product, admin_save_product_edit,
    admin_categories, admin_cat_view, admin_cat_add_start, _cat_name, _cat_emoji,
    admin_cat_edit_start, _cat_edit_save, admin_cat_toggle, admin_cat_feature, admin_cat_delete,
    admin_delivery, admin_dlv_view, admin_dlv_add_start, _dlv_name, _dlv_desc, _dlv_charge,
    admin_dlv_edit_start, _dlv_edit_save, admin_dlv_toggle, admin_dlv_delete,
    admin_payment_methods, admin_pm_view, admin_pm_edit_start, _pm_edit_save, admin_pm_toggle,
    admin_pm_add_start, _pm_name, _pm_num, _pm_desc,
    admin_coupons, admin_coupon_view, admin_coupon_add_start,
    _cpn_code, _cpn_type, _cpn_val, _cpn_min, _cpn_exp,
    admin_coupon_edit_start, _cpn_edit_save, admin_coupon_toggle, admin_coupon_delete,
    admin_broadcast_menu, admin_broadcast_all_prompt, admin_broadcast_send,
    admin_msg_user_prompt, _msg_user_id, _msg_user_text,
    admin_analytics, admin_customers, admin_low_stock,
    admin_view_tickets, admin_ticket_detail,
    admin_ticket_reply_prompt, admin_ticket_reply_send,
    admin_ticket_close, admin_ticket_reopen,
    BROADCAST_MSG, MSG_USER_ID, MSG_USER_TEXT,
    ADD_PROD_NAME, ADD_PROD_CAT, ADD_PROD_DESC, ADD_PROD_PRICE,
    ADD_PROD_DISC, ADD_PROD_STOCK, ADD_PROD_IMAGE, EDIT_PROD_VAL,
    ADD_CAT_NAME, ADD_CAT_EMOJI, EDIT_CAT_VAL,
    ADD_DLV_NAME, ADD_DLV_DESC, ADD_DLV_CHARGE, EDIT_DLV_VAL,
    ADD_PM_NAME, ADD_PM_NUM, ADD_PM_DESC, EDIT_PM_VAL,
    ADD_CPN_CODE, ADD_CPN_TYPE, ADD_CPN_VAL, ADD_CPN_MIN, ADD_CPN_EXP, EDIT_CPN_VAL,
    TICKET_REPLY_STATE, ORDER_NOTE_STATE,
)

async def error_handler(update: object, context) -> None:
    tb = "".join(traceback.format_exception(type(context.error), context.error, context.error.__traceback__))
    logger.error(f"❌ Exception:\n{tb}")
    if isinstance(update, Update):
        if update.effective_user:
            logger.error(f"   User: {update.effective_user.id} | CB: {getattr(update.callback_query,'data',None)}")
        if update.effective_message:
            try:
                err_short = str(context.error)[:300]
                await update.effective_message.reply_text(
                    f"⚠️ Error: `{type(context.error).__name__}`: {err_short}\n\n/start দিন।",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

def conv_checkout():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(buy_now, pattern=r"^buynow_\d+$"),
            CallbackQueryHandler(checkout_from_cart, pattern=r"^checkout$"),
        ],
        states={
            DELIVERY: [CallbackQueryHandler(get_delivery, pattern=r"^dlv_\d+$")],
            NAME:     [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            ADDRESS:  [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            NOTES:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_notes)],
            CONFIRM:  [
                CallbackQueryHandler(confirm_order,   pattern=r"^confirm_order$"),
                CallbackQueryHandler(cancel_checkout, pattern=r"^cancel_checkout$"),
            ],
        },
        fallbacks=[CallbackQueryHandler(cancel_checkout, pattern=r"^cancel_checkout$"), CommandHandler("start", start)],
        allow_reentry=True, name="checkout",
    )

def conv_payment():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(show_payment_instructions, pattern=r"^pay_\d+_\d+$")],
        states={WAITING_SCREENSHOT: [MessageHandler(filters.PHOTO, receive_screenshot)]},
        fallbacks=[CallbackQueryHandler(my_orders, pattern=r"^my_orders$"), CommandHandler("start", start)],
        allow_reentry=True, name="payment",
    )

def conv_search():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(search_prompt, pattern=r"^search_products$")],
        states={SEARCH_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_search_input)]},
        fallbacks=[CallbackQueryHandler(main_menu, pattern=r"^main_menu$"), CommandHandler("start", start)],
        allow_reentry=True, name="search",
    )

def conv_coupon():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(coupon_prompt, pattern=r"^use_coupon$")],
        states={COUPON_INPUT: [MessageHandler(filters.TEXT & ~filters.COMMAND, apply_coupon)]},
        fallbacks=[CallbackQueryHandler(main_menu, pattern=r"^main_menu$"), CommandHandler("start", start)],
        allow_reentry=True, name="coupon",
    )

def conv_ticket():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(new_ticket_prompt, pattern=r"^new_ticket$")],
        states={TICKET_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_ticket)]},
        fallbacks=[CallbackQueryHandler(customer_support, pattern=r"^support$"), CommandHandler("start", start)],
        allow_reentry=True, name="ticket",
    )

def conv_admin_broadcast():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_broadcast_all_prompt, pattern=r"^adm_broadcast_all$")],
        states={BROADCAST_MSG: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_broadcast_send)]},
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True, name="broadcast",
    )

def conv_msg_user():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_msg_user_prompt, pattern=r"^adm_msg_user$")],
        states={
            MSG_USER_ID:   [MessageHandler(filters.TEXT & ~filters.COMMAND, _msg_user_id)],
            MSG_USER_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, _msg_user_text)],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True, name="msg_user",
    )

def conv_add_product():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_add_product_start, pattern=r"^adm_add_product$")],
        states={
            ADD_PROD_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, _ap_name)],
            ADD_PROD_CAT:   [MessageHandler(filters.TEXT & ~filters.COMMAND, _ap_cat)],
            ADD_PROD_DESC:  [MessageHandler(filters.TEXT & ~filters.COMMAND, _ap_desc)],
            ADD_PROD_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, _ap_price)],
            ADD_PROD_DISC:  [MessageHandler(filters.TEXT & ~filters.COMMAND, _ap_disc)],
            ADD_PROD_STOCK: [MessageHandler(filters.TEXT & ~filters.COMMAND, _ap_stock)],
            ADD_PROD_IMAGE: [
                MessageHandler(filters.PHOTO, _ap_image),
                MessageHandler(filters.TEXT & ~filters.COMMAND, _ap_image),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True, name="add_product",
    )

def conv_edit_product():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_edit_product,
                pattern=r"^admprod_(name|price|discount|stock|image|desc|tags|featured|delete)_\d+$")
        ],
        states={
            EDIT_PROD_VAL: [
                MessageHandler(filters.PHOTO, admin_save_product_edit),
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_save_product_edit),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True, name="edit_product",
    )

def conv_add_category():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_cat_add_start, pattern=r"^adm_cat_add$")],
        states={
            ADD_CAT_NAME:  [MessageHandler(filters.TEXT & ~filters.COMMAND, _cat_name)],
            ADD_CAT_EMOJI: [MessageHandler(filters.TEXT & ~filters.COMMAND, _cat_emoji)],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True, name="add_cat",
    )

def conv_edit_category():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_cat_edit_start, pattern=r"^adm_cat_edit_(name|emoji)_\d+$")
        ],
        states={EDIT_CAT_VAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, _cat_edit_save)]},
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True, name="edit_cat",
    )

def conv_add_delivery():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_dlv_add_start, pattern=r"^adm_dlv_add$")],
        states={
            ADD_DLV_NAME:   [MessageHandler(filters.TEXT & ~filters.COMMAND, _dlv_name)],
            ADD_DLV_DESC:   [MessageHandler(filters.TEXT & ~filters.COMMAND, _dlv_desc)],
            ADD_DLV_CHARGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, _dlv_charge)],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True, name="add_dlv",
    )

def conv_edit_delivery():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_dlv_edit_start, pattern=r"^adm_dlv_edit_(name|charge)_\d+$")
        ],
        states={EDIT_DLV_VAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, _dlv_edit_save)]},
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True, name="edit_dlv",
    )

def conv_add_payment():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_pm_add_start, pattern=r"^adm_pm_add$")],
        states={
            ADD_PM_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, _pm_name)],
            ADD_PM_NUM:  [MessageHandler(filters.TEXT & ~filters.COMMAND, _pm_num)],
            ADD_PM_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, _pm_desc)],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True, name="add_pm",
    )

def conv_edit_payment():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_pm_edit_start, pattern=r"^adm_pm_edit_(name|number)_\d+$")
        ],
        states={EDIT_PM_VAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, _pm_edit_save)]},
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True, name="edit_pm",
    )

def conv_add_coupon():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_coupon_add_start, pattern=r"^adm_coupon_add$")],
        states={
            ADD_CPN_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, _cpn_code)],
            ADD_CPN_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, _cpn_type)],
            ADD_CPN_VAL:  [MessageHandler(filters.TEXT & ~filters.COMMAND, _cpn_val)],
            ADD_CPN_MIN:  [MessageHandler(filters.TEXT & ~filters.COMMAND, _cpn_min)],
            ADD_CPN_EXP:  [MessageHandler(filters.TEXT & ~filters.COMMAND, _cpn_exp)],
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True, name="add_coupon",
    )

def conv_edit_coupon():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_coupon_edit_start, pattern=r"^adm_coupon_edit_(code|val|exp)_\d+$")
        ],
        states={EDIT_CPN_VAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, _cpn_edit_save)]},
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True, name="edit_coupon",
    )

def conv_ticket_reply():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_ticket_reply_prompt, pattern=r"^adm_ticket_reply_\d+$")
        ],
        states={TICKET_REPLY_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_ticket_reply_send)]},
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True, name="ticket_reply",
    )

def conv_order_note():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_order_note_prompt, pattern=r"^adm_order_note_\d+$")
        ],
        states={ORDER_NOTE_STATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_order_note_save)]},
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True, name="order_note",
    )


def conv_review():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(handle_star_rating, pattern=r"^rate_\d+_[1-5]$")
        ],
        states={REVIEW_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_review_note)]},
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True, name="review",
    )


def build_application() -> Application:
    if not BOT_TOKEN:
        logger.critical("❌ BOT_TOKEN নেই!")
        sys.exit(1)

    app = Application.builder().token(BOT_TOKEN).build()

    # 1. Conversations first
    for conv in [
        conv_checkout(), conv_payment(), conv_search(), conv_coupon(), conv_ticket(),
        conv_admin_broadcast(), conv_msg_user(),
        conv_add_product(), conv_edit_product(),
        conv_add_category(), conv_edit_category(),
        conv_add_delivery(), conv_edit_delivery(),
        conv_add_payment(), conv_edit_payment(),
        conv_add_coupon(), conv_edit_coupon(),
        conv_ticket_reply(), conv_order_note(), conv_review(),
    ]:
        app.add_handler(conv)

    # 2. Commands
    app.add_handler(CommandHandler("start",  start))
    app.add_handler(CommandHandler("menu",   start))
    app.add_handler(CommandHandler("orders", my_orders))
    app.add_handler(CommandHandler("cart",   view_cart))
    app.add_handler(CommandHandler("track",  track_order))
    app.add_handler(CommandHandler("admin",  admin_panel))

    # 3. Admin
    app.add_handler(CallbackQueryHandler(admin_panel,             pattern=r"^adm_panel$"))
    app.add_handler(CallbackQueryHandler(admin_view_orders,       pattern=r"^adm_orders_\w+_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_view_order_detail, pattern=r"^adm_order_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_update_order,      pattern=r"^admupd_\d+_\w+$"))
    app.add_handler(CallbackQueryHandler(admin_list_products,     pattern=r"^adm_products_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_view_product,      pattern=r"^admprodview_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_categories,        pattern=r"^adm_categories$"))
    app.add_handler(CallbackQueryHandler(admin_cat_view,          pattern=r"^adm_cat_view_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_cat_toggle,        pattern=r"^adm_cat_toggle_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_cat_feature,       pattern=r"^adm_cat_feature_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_cat_delete,        pattern=r"^adm_cat_delete_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_delivery,          pattern=r"^adm_delivery$"))
    app.add_handler(CallbackQueryHandler(admin_dlv_view,          pattern=r"^adm_dlv_view_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_dlv_toggle,        pattern=r"^adm_dlv_toggle_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_dlv_delete,        pattern=r"^adm_dlv_delete_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_payment_methods,   pattern=r"^adm_payment_methods$"))
    app.add_handler(CallbackQueryHandler(admin_pm_view,           pattern=r"^adm_pm_view_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_pm_toggle,         pattern=r"^adm_pm_toggle_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_coupons,           pattern=r"^adm_coupons$"))
    app.add_handler(CallbackQueryHandler(admin_coupon_view,       pattern=r"^adm_coupon_view_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_coupon_toggle,     pattern=r"^adm_coupon_toggle_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_coupon_delete,     pattern=r"^adm_coupon_delete_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_broadcast_menu,    pattern=r"^adm_broadcast$"))
    app.add_handler(CallbackQueryHandler(admin_analytics,         pattern=r"^adm_analytics$"))
    app.add_handler(CallbackQueryHandler(admin_customers,         pattern=r"^adm_customers$"))
    app.add_handler(CallbackQueryHandler(admin_low_stock,         pattern=r"^adm_low_stock$"))
    app.add_handler(CallbackQueryHandler(admin_view_tickets,      pattern=r"^adm_tickets_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_ticket_detail,     pattern=r"^adm_ticket_view_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_ticket_close,      pattern=r"^adm_ticket_close_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_ticket_reopen,     pattern=r"^adm_ticket_reopen_\d+$"))

    # 4. User
    app.add_handler(CallbackQueryHandler(main_menu,               pattern=r"^main_menu$"))
    app.add_handler(CallbackQueryHandler(show_categories,         pattern=r"^browse_categories$"))
    app.add_handler(CallbackQueryHandler(show_featured_products,  pattern=r"^featured_products$"))
    app.add_handler(CallbackQueryHandler(show_bestsellers,        pattern=r"^bestseller_products$"))
    app.add_handler(CallbackQueryHandler(show_new_arrivals,       pattern=r"^new_arrivals$"))
    app.add_handler(CallbackQueryHandler(show_products_by_catid,  pattern=r"^catid_\d+(_p\d+)?$"))
    app.add_handler(CallbackQueryHandler(show_product_detail,     pattern=r"^product_\d+$"))
    app.add_handler(CallbackQueryHandler(add_to_cart_handler,     pattern=r"^addcart_\d+$"))
    app.add_handler(CallbackQueryHandler(view_cart,               pattern=r"^view_cart$"))
    app.add_handler(CallbackQueryHandler(cart_qty_handler,        pattern=r"^cartqty_\d+_(inc|dec)$"))
    app.add_handler(CallbackQueryHandler(cart_del_handler,        pattern=r"^cartdel_\d+$"))
    app.add_handler(CallbackQueryHandler(clear_cart_handler,      pattern=r"^clear_cart$"))
    app.add_handler(CallbackQueryHandler(share_product,           pattern=r"^share_\d+$"))
    app.add_handler(CallbackQueryHandler(select_payment,          pattern=r"^payorder_\d+$"))
    app.add_handler(CallbackQueryHandler(my_orders,               pattern=r"^my_orders$"))
    app.add_handler(CallbackQueryHandler(view_order_detail,       pattern=r"^vieworder_\d+$"))
    app.add_handler(CallbackQueryHandler(track_order,             pattern=r"^track_order$"))
    app.add_handler(CallbackQueryHandler(review_prompt,           pattern=r"^review_\d+$"))
    app.add_handler(CallbackQueryHandler(my_profile,              pattern=r"^my_profile$"))
    app.add_handler(CallbackQueryHandler(my_wishlist,             pattern=r"^my_wishlist$"))
    app.add_handler(CallbackQueryHandler(toggle_wishlist,         pattern=r"^wish_\d+$"))
    app.add_handler(CallbackQueryHandler(recently_viewed_handler, pattern=r"^recently_viewed$"))
    app.add_handler(CallbackQueryHandler(customer_support,        pattern=r"^support$"))
    app.add_handler(CallbackQueryHandler(my_tickets,              pattern=r"^my_tickets$"))
    app.add_handler(CallbackQueryHandler(noop,                    pattern=r"^noop$"))

    app.add_error_handler(error_handler)
    return app


def main():
    logger.info("🚀 PickDeal BD v3.1 চালু হচ্ছে...")
    initialize_database()
    app = build_application()
    logger.info("✅ Polling শুরু...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
