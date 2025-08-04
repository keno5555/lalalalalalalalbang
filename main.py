#!/usr/bin/env python3
"""
Telegram Music Bot - Main Entry Point
Runs Flask for Render and starts the Telegram bot (async).
"""

import logging
import os
import threading
import time
import asyncio
from flask import Flask, jsonify, render_template
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from bot.handlers import (
    start_command, help_command, handle_button_callback, handle_message
)

# Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Flask setup
app = Flask(__name__)
bot_status = {"running": False, "start_time": time.time(), "last_seen": 0}

@app.route('/')
def home():
    return "🎵 Telegram Music Bot is running!"

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "bot_running": bot_status["running"],
        "service": "Telegram Music Bot"
    })

@app.route('/status')
def status_page():
    return f"""
    <html><head><title>Bot Status</title></head>
    <body style="font-family:sans-serif;text-align:center;padding:40px;">
    <h1>🎶 Bot Status</h1>
    <p>Running: {'✅ Yes' if bot_status['running'] else '❌ No'}</p>
    <p>Uptime: {int(time.time() - bot_status['start_time'])}s</p>
    </body></html>
    """

@app.route('/api/status')
def api_status():
    return jsonify({
        "bot_running": bot_status["running"],
        "uptime": time.time() - bot_status["start_time"],
        "last_seen": bot_status["last_seen"]
    })

async def run_telegram_bot_async():
    """Run Telegram bot using async Application."""
    try:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            logger.error("❌ TELEGRAM_BOT_TOKEN not set in environment.")
            return

        application = Application.builder().token(bot_token).build()

        # Add handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CallbackQueryHandler(handle_button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        bot_status["running"] = True
        bot_status["last_seen"] = time.time()

        logger.info("🤖 Telegram bot starting...")
        await application.run_polling()

    except Exception as e:
        logger.error(f"❌ Error running Telegram bot: {e}")
        bot_status["running"] = False

def run_telegram_bot():
    """Run bot in a separate thread."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_telegram_bot_async())
    except Exception as e:
        logger.error(f"❌ Bot thread error: {e}")
        bot_status["running"] = False

def main():
    print("🚀 Starting Flask + Telegram bot service...")
    port = int(os.getenv("PORT", 5000))

    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()

    time.sleep(2)
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False, threaded=True)

if __name__ == "__main__":
    main()
