#!/usr/bin/env python3
import logging
import os
import threading
import time
import asyncio
from flask import Flask, jsonify, render_template
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from bot.handlers import (
    start_command, help_command, handle_spotify_url,
    handle_button_callback, handle_message
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
bot_status = {"running": False, "start_time": time.time(), "last_seen": 0}

@app.route('/')
def home():
    return "SpotifyPulse bot is running!"

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
    try:
        return render_template('status.html')
    except:
        return f"""
        <html>
        <head><title>MusicFlow Bot Status</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>🎵 MusicFlow Bot Status</h1>
            <p>Bot is {'✅ Running' if bot_status['running'] else '❌ Stopped'}</p>
            <p>Uptime: {int(time.time() - bot_status['start_time'])} seconds</p>
            <p>Service: Telegram Music Download Bot</p>
        </body>
        </html>
        """

@app.route('/api/status')
def api_status():
    return jsonify({
        "bot_running": bot_status["running"],
        "uptime": time.time() - bot_status.get("start_time", time.time()),
        "last_seen": bot_status["last_seen"],
        "service": "MusicFlow Bot"
    })

async def run_telegram_bot_async():
    try:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        if not bot_token:
            logger.error("TELEGRAM_BOT_TOKEN environment variable is required")
            return

        application = Application.builder().token(bot_token).build()

        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CallbackQueryHandler(handle_button_callback))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

        bot_status["running"] = True
        bot_status["last_seen"] = time.time()

        logger.info("Starting Telegram Music Bot...")
        await application.initialize()
        await application.start()
        await application.bot.set_my_commands([
            ("start", "Start the bot"),
            ("help", "Help and usage")
        ])
        await application.run_polling()
    except Exception as e:
        logger.error(f"❌ Error running Telegram bot: {e}")
        bot_status["running"] = False

def run_telegram_bot():
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_telegram_bot_async())
    except Exception as e:
        logger.error(f"Error in bot thread: {e}")
        bot_status["running"] = False

def main():
    print("🎵 Starting Telegram Music Bot with Flask Web Server...")
    port = int(os.environ.get("PORT", 5000))
    print(f"🌐 Port configuration: {port} (from PORT env var)")

    bot_thread = threading.Thread(target=run_telegram_bot, daemon=True)
    bot_thread.start()
    print("🤖 Telegram bot started in background thread...")
    time.sleep(2)

    print(f"🚀 Starting Flask web server on port {port}...")
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False,
        use_reloader=False,
        threaded=True
    )

if __name__ == "__main__":
    main()
