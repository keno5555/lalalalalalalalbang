"""
Telegram Bot Handlers
Contains all command and callback handlers for the music bot.
"""

import logging
import re
import asyncio
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from .spotify_client import SpotifyClient
from .audio_processor import AudioProcessor
from .demo_songs import DemoSongs
from .utils import create_quality_keyboard, create_main_keyboard, extract_spotify_id
from config import BOT_WELCOME, BOT_HELP, QUALITY_OPTIONS

logger = logging.getLogger(__name__)

# Initialize components
spotify_client = SpotifyClient()
audio_processor = AudioProcessor()
demo_songs = DemoSongs()

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command with attractive welcome message."""
    keyboard = create_main_keyboard()
    
    await update.message.reply_text(
        BOT_WELCOME,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command with detailed instructions."""
    keyboard = [[InlineKeyboardButton("🏠 Back to Main Menu", callback_data="main_menu")]]
    
    await update.message.reply_text(
        BOT_HELP,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming text messages (URLs)."""
    message_text = update.message.text.strip()
    
    # Check if it's a Spotify URL
    if "spotify.com" in message_text:
        await handle_spotify_url(update, context, message_text)
    else:
        # Guide user to use proper links
        keyboard = [[InlineKeyboardButton("🎪 Try Demo", callback_data="try_demo")]]
        await update.message.reply_text(
            "🤔 *Hmm, that doesn't look like a valid music link!*\n\n"
            "Please share a proper music platform link, or try our demo feature! 🎶",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_spotify_url(update: Update, context: ContextTypes.DEFAULT_TYPE, url: str):
    """Process Spotify URLs and initiate download flow."""
    # Send processing message
    processing_msg = await update.message.reply_text(
        "🔍 *Analyzing your request...*\n\n"
        "⏳ Please wait while I prepare everything for you! ✨",
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        # Extract Spotify ID and type
        spotify_id, content_type = extract_spotify_id(url)
        
        if content_type == "track":
            await handle_single_track(update, context, spotify_id, processing_msg)
        elif content_type == "playlist":
            await handle_playlist(update, context, spotify_id, processing_msg)
        elif content_type == "album":
            await handle_album(update, context, spotify_id, processing_msg)
        else:
            await processing_msg.edit_text(
                "🚫 *Oops! Unsupported link type.*\n\n"
                "Please share a track, playlist, or album link! 🎶",
                parse_mode=ParseMode.MARKDOWN
            )
            
    except Exception as e:
        logger.error(f"Error processing Spotify URL: {e}")
        await processing_msg.edit_text(
            "🚫 *Something went wrong!*\n\n"
            "Please check your link and try again. 🔄",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_single_track(update: Update, context: ContextTypes.DEFAULT_TYPE, track_id: str, processing_msg):
    """Handle single track download with quality selection."""
    try:
        # Get track metadata
        track_info = await spotify_client.get_track_info(track_id)
        
        if not track_info:
            await processing_msg.edit_text(
                "🚫 *Track not found!*\n\n"
                "Please check your link and try again. 🔄",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Store track info in context for later use
        context.user_data['current_track'] = track_info
        context.user_data['processing_msg_id'] = processing_msg.message_id
        
        # Create quality selection keyboard
        keyboard = create_quality_keyboard(track_id)
        
        await processing_msg.edit_text(
            f"🎶 *Found your track!*\n\n"
            f"🎤 **{track_info['name']}**\n"
            f"👨‍🎤 *by {track_info['artist']}*\n"
            f"⏱️ *Duration: {track_info['duration']}*\n\n"
            f"🎯 *Choose your preferred quality:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error handling single track: {e}")
        await processing_msg.edit_text(
            "🚫 *Error retrieving track information.*\n\n"
            "Please try again later! 🔄",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_playlist(update: Update, context: ContextTypes.DEFAULT_TYPE, playlist_id: str, processing_msg):
    """Handle playlist download."""
    try:
        # Get playlist info
        playlist_info = await spotify_client.get_playlist_info(playlist_id)
        
        if not playlist_info:
            await processing_msg.edit_text(
                "🚫 *Playlist not found!*\n\n"
                "Please check your link and try again. 🔄",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        track_count = len(playlist_info['tracks'])
        
        # Create quality selection for playlist
        keyboard = []
        for quality_text, quality_value in QUALITY_OPTIONS.items():
            button = InlineKeyboardButton(
                f"📥 {quality_text}", 
                callback_data=f"download_playlist_{playlist_id}_{quality_value}"
            )
            keyboard.append([button])
        keyboard.append([InlineKeyboardButton("🚫 Cancel", callback_data="cancel_download")])
        
        try:
            await processing_msg.edit_text(
                f"🎧 *Playlist Found!*\n\n"
                f"🎼 **{playlist_info['name']}**\n"
                f"👨‍🎤 *by {playlist_info['owner']}*\n"
                f"🎶 *{track_count} tracks*\n\n"
                f"🎯 *Choose quality to download all {track_count} tracks:*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        except Exception as edit_error:
            logger.error(f"Error editing message for playlist: {edit_error}")
            # Try sending a new message if edit fails
            await processing_msg.reply_text(
                f"🎧 *Playlist Found!*\n\n"
                f"🎼 **{playlist_info['name']}**\n"
                f"👨‍🎤 *by {playlist_info['owner']}*\n"
                f"🎶 *{track_count} tracks*\n\n"
                f"🎯 *Choose quality to download all {track_count} tracks:*",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        
        # Store playlist info
        context.user_data['current_playlist'] = playlist_info
        context.user_data['processing_msg_id'] = processing_msg.message_id
        
    except Exception as e:
        logger.error(f"Error handling playlist: {e}")
        await processing_msg.edit_text(
            "🚫 *Error retrieving playlist information.*\n\n"
            "Please try again later! 🔄",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_album(update: Update, context: ContextTypes.DEFAULT_TYPE, album_id: str, processing_msg):
    """Handle album download."""
    try:
        # Get album info
        album_info = await spotify_client.get_album_info(album_id)
        
        if not album_info:
            await processing_msg.edit_text(
                "🚫 *Album not found!*\n\n"
                "Please check your link and try again. 🔄",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        track_count = len(album_info['tracks'])
        
        # Create quality selection for album
        keyboard = []
        for quality_text, quality_value in QUALITY_OPTIONS.items():
            button = InlineKeyboardButton(
                f"💿 {quality_text}", 
                callback_data=f"download_album_{album_id}_{quality_value}"
            )
            keyboard.append([button])
        keyboard.append([InlineKeyboardButton("🚫 Cancel", callback_data="cancel_download")])
        
        await processing_msg.edit_text(
            f"💽 *Album Found!*\n\n"
            f"🎼 **{album_info['name']}**\n"
            f"👨‍🎤 *by {album_info['artist']}*\n"
            f"🎶 *{track_count} tracks*\n\n"
            f"🎯 *Choose quality to download all {track_count} tracks:*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        # Store album info
        context.user_data['current_album'] = album_info
        context.user_data['processing_msg_id'] = processing_msg.message_id
        
    except Exception as e:
        logger.error(f"Error handling album: {e}")
        await processing_msg.edit_text(
            "🚫 *Error retrieving album information.*\n\n"
            "Please try again later! 🔄",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all button callbacks."""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    logger.info(f"Received callback: {callback_data}")
    
    if callback_data == "main_menu":
        await show_main_menu(query, context)
    elif callback_data == "help":
        await show_help_info(query, context)
    elif callback_data == "try_demo":
        await show_demo_options(query, context)
    elif callback_data == "get_demo_url":
        await provide_demo_url(query, context)
    elif callback_data == "share_bot":
        await show_share_info(query, context)
    elif callback_data.startswith("quality_"):
        await handle_quality_selection(query, context)
    elif callback_data.startswith("download_"):
        await handle_download_request(query, context)
    elif callback_data == "cancel_download":
        await cancel_download(query, context)
    elif callback_data == "download_another":
        await handle_download_another(query, context)
    else:
        await query.message.reply_text("🤔 Unknown action. Please try again!")

async def show_main_menu(query, context):
    """Show main menu."""
    keyboard = create_main_keyboard()
    
    await query.edit_message_text(
        BOT_WELCOME,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_help_info(query, context):
    """Show help information."""
    keyboard = [[InlineKeyboardButton("🏠 Back to Main Menu", callback_data="main_menu")]]
    
    await query.edit_message_text(
        BOT_HELP,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_demo_options(query, context):
    """Show demo options."""
    keyboard = [
        [InlineKeyboardButton("🎲 Get Random Demo URL", callback_data="get_demo_url")],
        [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        "🎪 *Demo Mode*\n\n"
        "Test the bot with popular tracks! 🎶\n\n"
        "Click below to get a random demo link that you can copy and test! ✨",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def provide_demo_url(query, context):
    """Provide a random demo URL."""
    demo_url = demo_songs.get_random_demo_url()
    
    keyboard = [
        [InlineKeyboardButton("🎲 Another Demo URL", callback_data="get_demo_url")],
        [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        f"🎯 *Here's your demo link!*\n\n"
        f"`{demo_url}`\n\n"
        f"📋 *Tap to copy the link above, then send it back to me to test the download!* ✨\n\n"
        f"🔄 Want another demo link?",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def show_share_info(query, context):
    """Show bot sharing information."""
    bot_username = context.bot.username
    share_text = f"🎶 Check out this amazing MusicFlow Bot! @{bot_username} 🎶"
    share_url = f"https://t.me/share/url?url=https://t.me/{bot_username}&text={share_text}"
    
    keyboard = [
        [InlineKeyboardButton("📤 Share with Friends", url=share_url)],
        [InlineKeyboardButton("🏠 Back to Main Menu", callback_data="main_menu")]
    ]
    
    await query.edit_message_text(
        "📢 *Share MusicFlow Bot!*\n\n"
        "Help your friends discover seamless music downloads! 🎶✨\n\n"
        "Click the button below to share:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_quality_selection(query, context):
    """Handle quality selection for downloads."""
    quality = query.data.replace("quality_", "")
    track_info = context.user_data.get('current_track')
    
    if not track_info:
        await query.edit_message_text("❌ Session expired. Please send the link again!")
        return
    
    # Start download
    await start_track_download(query, context, track_info, quality)

async def start_track_download(query, context, track_info, quality):
    """Start downloading a single track."""
    # Remove keyboard (bubble effect)
    await query.edit_message_text(
        f"⬇️ *Downloading...*\n\n"
        f"🎶 **{track_info['name']}**\n"
        f"👨‍🎤 *by {track_info['artist']}*\n"
        f"🎯 *Quality: {quality}kbps*\n\n"
        f"⏳ Finding and processing your track...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        # Process download
        file_path = await audio_processor.download_track(track_info, quality)
        
        if file_path:
            # Get file size in MB
            file_size_bytes = os.path.getsize(file_path)
            file_size_mb = round(file_size_bytes / (1024 * 1024), 1)
            
            # Send the file with quality and size info
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
            
            # Create "Download Another" button
            keyboard = [[InlineKeyboardButton("🎵 Download Another", callback_data="download_another")]]
            
            # Update message to show completion with button
            await query.edit_message_text(
                f"✅ *Download Complete!*\n\n"
                f"🎶 **{track_info['name']}**\n"
                f"👨‍🎤 *by {track_info['artist']}*\n\n"
                f"Enjoy your music! 🎧✨",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        else:
            raise Exception("Download failed")
            
    except Exception as e:
        logger.error(f"Download error: {e}")
        await query.edit_message_text(
            f"❌ *Download failed!*\n\n"
            f"🎶 **{track_info['name']}**\n"
            f"👨‍🎤 *by {track_info['artist']}*\n\n"
            f"Please try again later. 🔄",
            parse_mode=ParseMode.MARKDOWN
        )

async def handle_download_request(query, context):
    """Handle playlist/album download requests with quality."""
    if query.data.startswith("download_playlist_"):
        parts = query.data.split("_")
        if len(parts) >= 4:  # download_playlist_id_quality
            quality = parts[-1]
            playlist_info = context.user_data.get('current_playlist')
            if playlist_info:
                await start_playlist_download(query, context, playlist_info, quality)
    elif query.data.startswith("download_album_"):
        parts = query.data.split("_")
        if len(parts) >= 4:  # download_album_id_quality
            quality = parts[-1]
            album_info = context.user_data.get('current_album')
            if album_info:
                await start_album_download(query, context, album_info, quality)

async def start_playlist_download(query, context, playlist_info, quality):
    """Start downloading playlist tracks with selected quality."""
    tracks = playlist_info['tracks']
    total_tracks = len(tracks)
    
    await query.edit_message_text(
        f"🚀 *Starting Playlist Download*\n\n"
        f"🎧 **{playlist_info['name']}**\n"
        f"🎶 *Processing {total_tracks} tracks...*\n"
        f"🎯 *Quality: {quality}kbps*\n\n"
        f"⏳ Sit back and enjoy while I get your music! 🎶",
        parse_mode=ParseMode.MARKDOWN
    )
    
    success_count = 0
    for i, track in enumerate(tracks, 1):
        try:
            # Update progress
            await query.edit_message_text(
                f"💫 *Downloading Playlist*\n\n"
                f"🎧 **{playlist_info['name']}**\n"
                f"🎶 *Track {i}/{total_tracks}*\n"
                f"🔥 **{track['name']}** by *{track['artist']}*\n\n"
                f"Progress: {'█' * (i * 10 // total_tracks)}{'░' * (10 - i * 10 // total_tracks)} {i * 100 // total_tracks}%",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Download track with selected quality
            file_path = await audio_processor.download_track(track, quality)
            
            if file_path:
                # Get file size in MB
                file_size_bytes = os.path.getsize(file_path)
                file_size_mb = round(file_size_bytes / (1024 * 1024), 1)
                
                await context.bot.send_audio(
                    chat_id=query.message.chat_id,
                    audio=open(file_path, 'rb'),
                    title=track['name'],
                    performer=track['artist'],
                    caption=f"💎 **{track['name']}** by *{track['artist']}*\n"
                           f"🎧 From playlist: *{playlist_info['name']}*\n\n"
                           f"🎯 *Quality:* {quality}kbps\n"
                           f"📁 *Size:* {file_size_mb} MB",
                    parse_mode=ParseMode.MARKDOWN
                )
                success_count += 1
                
        except Exception as e:
            logger.error(f"Error downloading track {track['name']}: {e}")
            continue
    
    # Create "Download Another" button
    keyboard = [[InlineKeyboardButton("🎵 Download Another", callback_data="download_another")]]
    
    # Final summary
    await query.edit_message_text(
        f"🎉 *Playlist Download Complete!*\n\n"
        f"🎧 **{playlist_info['name']}**\n"
        f"💎 *Successfully downloaded: {success_count}/{total_tracks} tracks*\n\n"
        f"Enjoy your amazing music collection! 🎶✨",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def start_album_download(query, context, album_info, quality):
    """Start downloading album tracks."""
    tracks = album_info['tracks']
    total_tracks = len(tracks)
    
    await query.edit_message_text(
        f"🚀 *Starting Album Download*\n\n"
        f"💽 **{album_info['name']}**\n"
        f"🎶 *Processing {total_tracks} tracks...*\n"
        f"🎯 *Quality: {quality}kbps*\n\n"
        f"⏳ Sit back and enjoy while I get your music! 🎶",
        parse_mode=ParseMode.MARKDOWN
    )
    
    success_count = 0
    for i, track in enumerate(tracks, 1):
        try:
            # Update progress
            await query.edit_message_text(
                f"💫 *Downloading Album*\n\n"
                f"💽 **{album_info['name']}**\n"
                f"🎶 *Track {i}/{total_tracks}*\n"
                f"🔥 **{track['name']}** by *{track['artist']}*\n\n"
                f"Progress: {'█' * (i * 10 // total_tracks)}{'░' * (10 - i * 10 // total_tracks)} {i * 100 // total_tracks}%",
                parse_mode=ParseMode.MARKDOWN
            )
            
            # Download track with selected quality
            file_path = await audio_processor.download_track(track, quality)
            
            if file_path:
                # Get file size in MB
                file_size_bytes = os.path.getsize(file_path)
                file_size_mb = round(file_size_bytes / (1024 * 1024), 1)
                
                await context.bot.send_audio(
                    chat_id=query.message.chat_id,
                    audio=open(file_path, 'rb'),
                    title=track['name'],
                    performer=track['artist'],
                    caption=f"💎 **{track['name']}** by *{track['artist']}*\n"
                           f"💽 From album: *{album_info['name']}*\n\n"
                           f"🎯 *Quality:* {quality}kbps\n"
                           f"📁 *Size:* {file_size_mb} MB",
                    parse_mode=ParseMode.MARKDOWN
                )
                success_count += 1
                
        except Exception as e:
            logger.error(f"Error downloading track {track['name']}: {e}")
            continue
    
    # Create "Download Another" button
    keyboard = [[InlineKeyboardButton("🎵 Download Another", callback_data="download_another")]]
    
    # Final summary
    await query.edit_message_text(
        f"🎉 *Album Download Complete!*\n\n"
        f"💽 **{album_info['name']}**\n"
        f"💎 *Successfully downloaded: {success_count}/{total_tracks} tracks*\n\n"
        f"Enjoy your amazing music collection! 🎶✨",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def cancel_download(query, context):
    """Cancel download process."""
    await query.edit_message_text(
        "🚫 *Download Cancelled*\n\n"
        "No worries! Feel free to try again anytime. 🎵",
        parse_mode=ParseMode.MARKDOWN
    )

async def handle_download_another(query, context):
    """Handle 'Download Another' button press."""
    logger.info("Download Another button pressed!")
    keyboard = create_main_keyboard()
    
    await query.edit_message_text(
        "🎵 *Ready for more music!*\n\n"
        "Share another Spotify link or try our demo features! 🎶",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
