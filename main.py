import logging
import asyncio
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from bot.handlers import (
    start_command,
    help_command,
    handle_button_callback,
    handle_message,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    try:
        application = (
            ApplicationBuilder()
            .token("YOUR_TELEGRAM_BOT_TOKEN")  # Replace this with os.getenv("TELEGRAM_BOT_TOKEN") if using .env
            .build()
        )

        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CallbackQueryHandler(handle_button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        logger.info("Bot is polling...")
        await application.run_polling()
    except Exception as e:
        logger.error(f"❌ Error running Telegram bot: {e}")

if __name__ == "__main__":
    asyncio.run(main())
