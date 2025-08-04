import os
import logging
import asyncio
import yt_dlp
from typing import Dict, Optional
import tempfile
import hashlib

logger = logging.getLogger(__name__)

class AudioProcessor:
    def __init__(self):
        self.download_dir = tempfile.mkdtemp(prefix="music_bot_")
        logger.info(f"Audio processor initialized with download directory: {self.download_dir}")

    async def download_track(self, track_info: Dict, quality: str) -> Optional[str]:
        search_query = f"{track_info['name']} {track_info['artist']}"
        logger.info(f"Searching for: {search_query}")

        # Try YT Music first, fallback to SoundCloud
        for source in [f"ytsearch1:{search_query} ytmusic", f"scsearch1:{search_query}"]:
            try:
                file_path = await self._attempt_download(source, track_info, quality)
                if file_path:
                    logger.info(f"Successfully downloaded: {file_path}")
                    return file_path
            except Exception as e:
                logger.error(f"Download failed from source {source}: {e}")
        
        logger.error(f"Download failed for all sources: {search_query}")
        return None

    async def _attempt_download(self, search_query: str, track_info: Dict, quality: str) -> Optional[str]:
        loop = asyncio.get_event_loop()
        return await asyncio.wait_for(
            loop.run_in_executor(None, self._download_audio, search_query, track_info, quality),
            timeout=60
        )

    def _download_audio(self, search_query: str, track_info: Dict, quality: str) -> Optional[str]:
        file_hash = hashlib.md5(search_query.encode()).hexdigest()[:8]
        output_name = f"{track_info['name']} - {track_info['artist']} [{file_hash}]"
        output_path = os.path.join(self.download_dir, f"{output_name}.%(ext)s")

        ydl_opts = self._get_ydl_options(quality)
        ydl_opts["outtmpl"] = output_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=True)
                base_path = ydl.prepare_filename(info).rsplit(".", 1)[0]
                for ext in [".mp3", ".m4a", ".webm", ".ogg"]:
                    full_path = base_path + ext
                    if os.path.exists(full_path):
                        return full_path
        except Exception as e:
            logger.error(f"yt-dlp download error: {e}")
            return None

    def _get_ydl_options(self, quality: str) -> Dict:
        format_map = {
            "128": "bestaudio[abr<=128]",
            "192": "bestaudio[abr<=192]",
            "320": "bestaudio/best"
        }

        return {
            "format": format_map.get(quality, "bestaudio[abr<=192]"),
            "quiet": True,
            "noplaylist": True,
            "no_warnings": True,
            "outtmpl": "",
            "ignoreerrors": True,
            "socket_timeout": 20,
            "retries": 3,
            "fragment_retries": 3,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": quality
            }]
        }

    def cleanup_file(self, file_path: str):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Deleted: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to delete file: {e}")

    def cleanup_all(self):
        try:
            for f in os.listdir(self.download_dir):
                self.cleanup_file(os.path.join(self.download_dir, f))
            os.rmdir(self.download_dir)
            logger.info("Cleaned up all downloads")
        except Exception as e:
            logger.warning(f"Cleanup error: {e}")