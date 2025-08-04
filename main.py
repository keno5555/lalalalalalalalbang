import logging
import os
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from bot.handlers import (
    start_command,
    help_command,
    handle_message,
    handle_button_callback,
)

# Logging Configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    try:
        # Read bot token from environment variable
        TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        if not TOKEN:
            raise ValueError("TELEGRAM_BOT_TOKEN not set in environment variables.")

        # Create Application instance (new way)
        app = ApplicationBuilder().token(TOKEN).build()

        # Register handlers
        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CallbackQueryHandler(handle_button_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        logger.info("✅ Bot started successfully.")
        app.run_polling()

    except Exception as e:
        logger.error(f"❌ Error running Telegram bot: {e}")

if __name__ == "__main__":
    main()
