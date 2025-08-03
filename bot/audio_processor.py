import os
import logging
import asyncio
import yt_dlp
from typing import Dict, Optional
import tempfile
import hashlib

logger = logging.getLogger(__name__)

class AudioProcessor:
    """Handles audio search and download operations."""
    
    def __init__(self):
        self.download_dir = tempfile.mkdtemp(prefix="music_bot_")
        logger.info(f"Audio processor initialized with download directory: {self.download_dir}")

    async def download_track(self, track_info: Dict, quality: str) -> Optional[str]:
        search_query = f"{track_info['name']} {track_info['artist']}"
        logger.info(f"Starting download for: {search_query}")

        # File naming
        file_hash = hashlib.md5(search_query.encode()).hexdigest()[:8]
        output_filename = f"{track_info['name']} - {track_info['artist']} [{file_hash}].%(ext)s"
        output_path = os.path.join(self.download_dir, output_filename)

        # yt-dlp options
        ydl_opts = {
            "format": f"bestaudio[abr<= {quality}]/bestaudio/best",
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "cookiefile": "./cookies.txt",  # ✅ Place your cookies.txt in root
            "outtmpl": output_path,
            "postprocessors": [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "mp3",
                    "preferredquality": quality,
                }
            ],
            "retries": 2,
            "socket_timeout": 10,
        }

        # Fallback search platforms
        sources = [
            f"ytsearch1:{search_query}",
            f"scsearch1:{search_query}",      # SoundCloud
            f"ytmusicsearch1:{search_query}"  # YouTube Music
        ]

        for source in sources:
            try:
                logger.info(f"Trying: {source}")
                loop = asyncio.get_event_loop()
                file_path = await asyncio.wait_for(
                    loop.run_in_executor(None, self._download_audio, source, ydl_opts),
                    timeout=60
                )
                if file_path and os.path.exists(file_path):
                    logger.info(f"Download succeeded: {file_path}")
                    return file_path
            except asyncio.TimeoutError:
                logger.error(f"Timeout for: {source}")
            except Exception as e:
                logger.error(f"yt-dlp download error: {e}")

        logger.error(f"Download failed for: {search_query}")
        return None

    def _download_audio(self, query: str, ydl_opts: Dict) -> Optional[str]:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=True)
                if "entries" in info:
                    info = info["entries"][0]
                filepath = ydl.prepare_filename(info)
                base, _ = os.path.splitext(filepath)

                # Look for final audio file
                for ext in [".mp3", ".m4a", ".webm", ".ogg"]:
                    full_path = base + ext
                    if os.path.exists(full_path):
                        return full_path

                return None
        except Exception as e:
            logger.error(f"yt-dlp download error: {e}")
            return None

    def cleanup_file(self, file_path: str):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up file: {file_path}")
        except Exception as e:
            logger.warning(f"Cleanup failed for {file_path}: {e}")

    def cleanup_all(self):
        try:
            for file in os.listdir(self.download_dir):
                self.cleanup_file(os.path.join(self.download_dir, file))
            os.rmdir(self.download_dir)
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")