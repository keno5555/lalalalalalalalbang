import os
import logging
import asyncio
import yt_dlp
import tempfile
import hashlib
import httpx
from bs4 import BeautifulSoup
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class AudioProcessor:
    def __init__(self):
        self.download_dir = tempfile.mkdtemp(prefix="music_bot_")
        logger.info(f"Download dir: {self.download_dir}")

    async def download_track(self, track_info: Dict, quality: str) -> Optional[str]:
        query = f"{track_info['name']} {track_info['artist']}"
        logger.info(f"Searching via Y2Mate: {query}")
        return await self._download_with_y2mate(query, quality)

    async def _download_with_y2mate(self, search_query: str, quality: str) -> Optional[str]:
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                search_url = f"https://www.youtube.com/results?search_query={search_query.replace(' ', '+')}"
                res = await client.get(search_url)

            soup = BeautifulSoup(res.text, "html.parser")
            video_links = [
                a["href"] for a in soup.find_all("a", href=True)
                if "/watch?v=" in a["href"]
            ]
            if not video_links:
                logger.error("Y2Mate: No YouTube video found.")
                return None

            video_id = video_links[0].split("v=")[-1].split("&")[0]
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            logger.info(f"Y2Mate: Using video {video_url}")

            return await self._download_with_yt_dlp(video_url, search_query, quality)

        except Exception as e:
            logger.error(f"Y2Mate fetch error: {e}")
            return None

    async def _download_with_yt_dlp(self, video_url: str, tag: str, quality: str) -> Optional[str]:
        ydl_opts = self._get_ydl_options(quality)
        file_hash = hashlib.md5(tag.encode()).hexdigest()[:8]
        output_filename = f"{tag} [{file_hash}].%(ext)s"
        ydl_opts['outtmpl'] = os.path.join(self.download_dir, output_filename)

        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(
                loop.run_in_executor(None, self._yt_dlp_download, video_url, ydl_opts),
                timeout=90
            )
        except Exception as e:
            logger.error(f"yt-dlp error: {e}")
            return None

    def _yt_dlp_download(self, url: str, ydl_opts: Dict) -> Optional[str]:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                path = ydl.prepare_filename(info)
                base = os.path.splitext(path)[0]
                for ext in ['.mp3', '.m4a', '.webm', '.opus']:
                    full = base + ext
                    if os.path.exists(full):
                        return full
        except Exception as e:
            logger.error(f"yt-dlp download error: {e}")
        return None

    def _get_ydl_options(self, quality: str) -> Dict:
        fmt = 'bestaudio[abr<=128]/bestaudio' if quality == '128' else 'bestaudio/best'
        return {
            'format': fmt,
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'retries': 2,
            'socket_timeout': 20,
        }

    def cleanup_file(self, file_path: str):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed cleanup: {e}")

    def cleanup_all(self):
        try:
            for file in os.listdir(self.download_dir):
                self.cleanup_file(os.path.join(self.download_dir, file))
            os.rmdir(self.download_dir)
            logger.info("All files cleaned up")
        except Exception as e:
            logger.warning(f"Failed full cleanup: {e}")
