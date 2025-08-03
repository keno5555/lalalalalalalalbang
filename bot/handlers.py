# ... [everything before this remains the same, until inside start_track_download]

async def start_track_download(query, context, track_info, quality):
    """Start downloading a single track."""
    await query.edit_message_text(
        f"⬇️ *Downloading...*\n\n"
        f"🎶 **{track_info['name']}**\n"
        f"👨‍🎤 *by {track_info['artist']}*\n"
        f"🎯 *Quality: {quality}kbps*\n\n"
        f"⏳ Finding and processing your track...",
        parse_mode=ParseMode.MARKDOWN
    )
    
    try:
        # 🔍 Logging before download
        logger.info(f"Calling audio_processor.download_track for {track_info['name']} at {quality}kbps")

        # Actual download
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

# ... Do the same patch in playlist/album handlers:

# Replace:
# file_path = await audio_processor.download_track(track, quality)

# With:
# logger.info(f"Downloading {track['name']} at {quality}kbps")
# file_path = await audio_processor.download_track(track, quality)
# logger.info(f"Returned path: {file_path}")