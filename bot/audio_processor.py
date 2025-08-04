"""
Audio Processing Module
Handles audio search and download functionality.
"""

import os
import logging
import asyncio
from typing import Dict, Optional
import tempfile
import hashlib
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class AudioProcessor:
    def __init__(self):
        self.download_dir = tempfile.mkdtemp(prefix="music_bot_")
        logger.info(f"Audio processor initialized with download directory: {self.download_dir}")

    async def download_track(self, track_info: Dict, quality: str) -> Optional[str]:
        try:
            search_query = f"{track_info['name']} {track_info['artist']}"
            logger.info(f"Searching Y2Mate for: {search_query}")

            file_path = await self._download_from_y2mate(search_query)

            if file_path and os.path.exists(file_path):
                logger.info(f"Successfully downloaded via Y2Mate: {file_path}")
                return file_path
            else:
                logger.error(f"Download failed for: {search_query}")
                return None

        except Exception as e:
            logger.error(f"Error downloading track {track_info['name']}: {e}")
            return None

    async def _download_from_y2mate(self, search_query: str) -> Optional[str]:
        try:
            logger.info(f"Searching on Y2Mate: {search_query}")
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self._scrape_y2mate, search_query)
        except Exception as e:
            logger.error(f"Y2Mate search error: {e}")
            return None

    def _scrape_y2mate(self, query: str) -> Optional[str]:
        try:
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://www.y2mate.is"
            }
            search_url = f"https://www.y2mate.is/m/ajax/search"
            response = requests.post(search_url, headers=headers, data={"q": query})
            soup = BeautifulSoup(response.text, "html.parser")

            link = None
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if "mp3" in href or ".mp3" in href:
                    link = href
                    break

            if not link:
                logger.error("Y2Mate: No MP3 links found")
                return None

            filename = f"{query.replace(' ', '_')}.mp3"
            filepath = os.path.join(self.download_dir, filename)

            file_data = requests.get(link, headers=headers)
            with open(filepath, "wb") as f:
                f.write(file_data.content)

            return filepath
        except Exception as e:
            logger.error(f"Failed to download from Y2Mate: {e}")
            return None

    def cleanup_file(self, file_path: str):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup file {file_path}: {e}")

    def cleanup_all(self):
        try:
            for file in os.listdir(self.download_dir):
                file_path = os.path.join(self.download_dir, file)
                self.cleanup_file(file_path)
            os.rmdir(self.download_dir)
            logger.info("All files cleaned up successfully")
        except Exception as e:
            logger.warning(f"Failed to cleanup all files: {e}")