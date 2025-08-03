"""
Audio Processing Module
Handles audio search and download functionality.
"""

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
        """
        Download track audio file with timeout handling.

        Args:
            track_info: Track information dictionary
            quality: Quality preference (128, 192, 320)

        Returns:
            Path to downloaded file or None if failed
        """
        try:
            search_query = f"{track_info['name']} {track_info['artist']}"
            logger.info(f"Searching for: {search_query}")

            ydl_opts = self._get_ydl_options(quality)
            file_hash = hashlib.md5(search_query.encode()).hexdigest()[:8]
            output_filename = f"{track_info['name']} - {track_info['artist']} [{file_hash}].%(ext)s"
            ydl_opts['outtmpl'] = os.path.join(self.download_dir, output_filename)

            loop = asyncio.get_event_loop()

            sources = [
                f"scsearch1:{search_query}",
                f"ytmusicsearch1:{search_query}"
            ]

            for source in sources:
                logger.info(f"Trying: {source}")
                try:
                    file_path = await asyncio.wait_for(
                        loop.run_in_executor(None, self._download_audio, source, ydl_opts),
                        timeout=60
                    )
                    if file_path and os.path.exists(file_path):
                        logger.info(f"Successfully downloaded: {file_path}")
                        return file_path
                except Exception as e:
                    logger.error(f"yt-dlp download error: {e}")

            logger.error(f"Download failed for all sources: {search_query}")
            return None

        except Exception as e:
            logger.error(f"Error downloading track {track_info['name']}: {e}")
            return None

    def _download_audio(self, search_query: str, ydl_opts: Dict) -> Optional[str]:
        """
        Internal method to download audio using yt-dlp.

        Args:
            search_query: Search query string
            ydl_opts: yt-dlp options

        Returns:
            Path to downloaded file or None
        """
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(search_query, download=True)
                if 'entries' in result:
                    result = result['entries'][0]
                filename = ydl.prepare_filename(result)
                base, _ = os.path.splitext(filename)
                for ext in ['.mp3', '.m4a', '.webm', '.opus']:
                    if os.path.exists(base + ext):
                        return base + ext
                return None
        except Exception as e:
            logger.error(f"yt-dlp download error: {e}")
            return None

    def _get_ydl_options(self, quality: str) -> Dict:
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
            'no_warnings': True,
            'noplaylist': True,
            'outtmpl': '',  # set later
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': quality
            }],
        }
        return ydl_opts