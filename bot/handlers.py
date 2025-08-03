import logging
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode
from config import BOT_WELCOME, BOT_HELP
from .audio_processor import AudioProcessor
from .utils import create_main_keyboard, extract_spotify_id
from .spotify_client import SpotifyClient

logger = logging.getLogger(__name__)
audio_processor = AudioProcessor()
spotify_client = SpotifyClient()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = create_main_keyboard()
    await update.message.reply_text(
        BOT_WELCOME,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🏠 Back to Main Menu", callback_data="main_menu")]]
    await update.message.reply_text(
        BOT_HELP,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_spotify_url(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    processing_msg = await update.message.reply_text(
        "🔍 *Analyzing your request...*\n\n"
        "⏳ Please wait while I prepare everything for you! ✨",
        parse_mode=ParseMode.MARKDOWN
    )

    try:
        spotify_id, content_type = extract_spotify_id(url)

        if content_type == "track":
            track_info = await spotify_client.get_track_info(spotify_id)
            if not track_info:
                raise Exception("Track not found.")

            context.user_data['current_track'] = track_info
            keyboard = [[InlineKeyboardButton("Download", callback_data=f"quality_320")]]
            await processing_msg.edit_text(
                f"🎶 *Found your track!*\n\n"
                f"🎤 **{track_info['name']}**\n"
                f"👨‍🎤 *by {track_info['artist']}*\n"
                f"⏱️ *Duration: {track_info['duration']}*\n\n"
                f"🎯 *Choose your preferred quality:*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await processing_msg.edit_text(
                "🚫 *Only Spotify tracks are supported right now.*",
                parse_mode=ParseMode.MARKDOWN
            )

    except Exception as e:
        logger.error(f"Error in handle_spotify_url: {e}")
        await processing_msg.edit_text(
            "🚫 *Something went wrong while processing your link.*\n\n"
            "Please try again later.",
            parse_mode=ParseMode.MARKDOWN
        )

async def start_track_download(query, context, track_info, quality):
    await query.edit_message_text(
        f"⬇️ *Downloading...*\n\n"
        f"🎶 **{track_info['name']}**\n"
        f"👨‍🎤 *by {track_info['artist']}*\n"
        f"🎯 *Quality: {quality}kbps*\n\n"
        f"⏳ Finding and processing your track...",
        parse_mode=ParseMode.MARKDOWN
    )

    try:
        logger.info(f"Calling audio_processor.download_track for {track_info['name']} at {quality}kbps")
        file_path = await audio_processor.download_track(track_info, quality)
        logger.info(f"Download returned path: {file_path}")

        if file_path:
            file_size_bytes = os.path.getsize(file_path)
            file_size_mb = round(file_size_bytes / (1024 * 1024), 1)

            await context.bot.send_audio(
                chat_id=query.message.chat_id,
                audio=open(file_path, 'rb'),
                title=track_info['name'],
                performer=track_info['artist'],
                duration=track_info['duration_ms'] // 1000,
                caption=f"🎶 **{track_info['name']}** by *{track_info['artist']}*\n\n"
                        f"🎯 *Quality:* {quality}kbps\n"
                        f"📁 *Size:* {file_size_mb} MB\n"
                        f"⏱️ *Duration:* {track_info['duration']}\n\n"
                        f"Enjoy your music! 🎧✨",
                parse_mode=ParseMode.MARKDOWN
            )

            keyboard = [[InlineKeyboardButton("🎵 Download Another", callback_data="download_another")]]
            await query.edit_message_text(
                f"✅ *Download Complete!*\n\n"
                f"🎶 **{track_info['name']}**\n"
                f"👨‍🎤 *by {track_info['artist']}*\n\n"
                f"Enjoy your music! 🎧✨",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            raise Exception("Download failed — no file path returned")

    except Exception as e:
        logger.error(f"Download error: {e}")
        await query.edit_message_text(
            f"❌ *Download failed!*\n\n"
            f"🎶 **{track_info['name']}**\n"
            f"👨‍🎤 *by {track_info['artist']}*\n\n"
            f"Please try again later. 🔄",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("quality_"):
        quality = int(data.split("_")[1])
        track_info = context.user_data.get("current_track")

        if track_info:
            await start_track_download(query, context, track_info, quality)
        else:
            await query.edit_message_text(
                "⚠️ *Track info missing. Please try again from the beginning.*",
                parse_mode=ParseMode.MARKDOWN
            )

    elif data == "download_another":
        await query.edit_message_text(
            "📥 *Send me another Spotify track link!*",
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "main_menu":
        keyboard = create_main_keyboard()
        await query.edit_message_text(
            BOT_WELCOME,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif data == "try_demo":
        await query.edit_message_text(
            "🎧 *Here's how the bot works:*\n\n"
            "1️⃣ Paste a Spotify track link\n"
            "2️⃣ Tap on a quality button\n"
            "3️⃣ Receive your MP3 🎶\n\n"
            "Try sending a link now!",
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "features":
        await query.edit_message_text(
            "✨ *Bot Features:*\n"
            "• Spotify to MP3\n"
            "• Choose quality\n"
            "• Fast download\n"
            "• No ads, no login",
            parse_mode=ParseMode.MARKDOWN
        )

    elif data == "support":
        await query.edit_message_text(
            "💬 *Need help?*\n"
            "[Contact the developer](https://t.me/YOUR_SUPPORT_USERNAME)",
            parse_mode=ParseMode.MARKDOWN
        )

    else:
        logger.warning(f"❗ Unknown callback_data received: {data}")
        await query.edit_message_text(
            f"❓ *Unknown action:* `{data}`",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message_text = update.message.text.strip()

    if "open.spotify.com/track" in message_text:
        await handle_spotify_url(update, context, message_text)
    else:
        await update.message.reply_text(
            "❓ *Please send a valid Spotify track link.*",
            parse_mode=ParseMode.MARKDOWN
        )