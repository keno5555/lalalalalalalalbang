import asyncio
import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)
from bot.handlers import (
    start_command,
    help_command,
    handle_button_callback,
    handle_message
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def run_telegram_bot_async():
    try:
        import config

        # Create the application
        application = ApplicationBuilder().token(config.TELEGRAM_BOT_TOKEN).build()

        # Register handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CallbackQueryHandler(handle_button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        # Start the bot
        logger.info("Starting Telegram Music Bot...")
        await application.initialize()
        await application.start()
        await application.bot.set_my_commands([
            ("start", "Start the bot"),
            ("help", "Get help"),
        ])
        await application.run_polling()

    except Exception as e:
        logger.error(f"Error running Telegram bot: {e}")

if __name__ == "__main__":
    asyncio.run(run_telegram_bot_async())
