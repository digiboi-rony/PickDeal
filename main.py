"""
PickDeal BD - Telegram E-Commerce Bot
=====================================
Main entry point for the bot application.
Run this file to start the bot.
"""

import logging
import os
from dotenv import load_dotenv
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)

# Load environment variables from .env file
load_dotenv()

# Import handlers
from handlers.start_handler import start, main_menu
from handlers.product_handler import (
    show_categories,
    show_products,
    show_product_detail,
    BROWSING,
)
from handlers.order_handler import (
    start_order,
    get_name,
    get_phone,
    get_address,
    get_quantity,
    confirm_order,
    cancel_order,
    NAME, PHONE, ADDRESS, QUANTITY, CONFIRM,
)
from handlers.payment_handler import (
    show_payment_instructions,
    receive_payment_screenshot,
    WAITING_SCREENSHOT,
)
from handlers.tracking_handler import track_order, my_orders
from handlers.support_handler import customer_support
from handlers.admin_handler import (
    admin_panel,
    admin_view_orders,
    admin_update_order,
    admin_search_order,
    admin_broadcast,
    admin_send_broadcast,
    BROADCAST,
)
from database.db_setup import initialize_database

# ─── Logging Setup ──────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot.log"),
    ],
)
logger = logging.getLogger(__name__)


def main():
    """Main function to start the Telegram bot."""
    
    # Get bot token from environment variable
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        logger.error("❌ BOT_TOKEN not found! Please set it in .env file.")
        raise ValueError("BOT_TOKEN environment variable is required.")

    # Initialize database (create tables if they don't exist)
    logger.info("🗄️  Initializing database...")
    initialize_database()
    logger.info("✅ Database ready!")

    # Build the Telegram application
    app = Application.builder().token(bot_token).build()

    # ─── Order ConversationHandler ───────────────────────────────────────────
    order_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_order, pattern="^order_")],
        states={
            NAME:     [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            PHONE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            ADDRESS:  [MessageHandler(filters.TEXT & ~filters.COMMAND, get_address)],
            QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_quantity)],
            CONFIRM:  [CallbackQueryHandler(confirm_order, pattern="^(confirm_order|cancel_order)$")],
        },
        fallbacks=[CommandHandler("cancel", cancel_order)],
    )

    # ─── Payment ConversationHandler ─────────────────────────────────────────
    payment_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(show_payment_instructions, pattern="^pay_order_")],
        states={
            WAITING_SCREENSHOT: [
                MessageHandler(filters.PHOTO, receive_payment_screenshot)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_order)],
    )

    # ─── Admin Broadcast ConversationHandler ─────────────────────────────────
    broadcast_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_broadcast, pattern="^admin_broadcast$")],
        states={
            BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_send_broadcast)],
        },
        fallbacks=[CommandHandler("cancel", cancel_order)],
    )

    # ─── Register Handlers ───────────────────────────────────────────────────
    # Core commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("orders", my_orders))
    app.add_handler(CommandHandler("track", track_order))

    # Conversation handlers (must come before general callback handler)
    app.add_handler(order_conv)
    app.add_handler(payment_conv)
    app.add_handler(broadcast_conv)

    # Callback query handlers for navigation
    app.add_handler(CallbackQueryHandler(main_menu,           pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(show_categories,     pattern="^browse_products$"))
    app.add_handler(CallbackQueryHandler(show_products,       pattern="^cat_"))
    app.add_handler(CallbackQueryHandler(show_product_detail, pattern="^product_"))
    app.add_handler(CallbackQueryHandler(my_orders,           pattern="^my_orders$"))
    app.add_handler(CallbackQueryHandler(track_order,         pattern="^track_order$"))
    app.add_handler(CallbackQueryHandler(customer_support,    pattern="^support$"))

    # Admin callback handlers
    app.add_handler(CallbackQueryHandler(admin_panel,        pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(admin_view_orders,  pattern="^admin_orders"))
    app.add_handler(CallbackQueryHandler(admin_update_order, pattern="^admin_update_"))
    app.add_handler(CallbackQueryHandler(admin_search_order, pattern="^admin_search$"))

    # ─── Start the Bot ───────────────────────────────────────────────────────
    logger.info("🤖 PickDeal BD Bot is starting...")
    logger.info("🚀 Bot is running! Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
