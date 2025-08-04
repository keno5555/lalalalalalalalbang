import os
import logging
import asyncio
import yt_dlp
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
        search_query = f"{track_info['name']} {track_info['artist']}"
        logger.info(f"Searching for: {search_query}")
        file_hash = hashlib.md5(search_query.encode()).hexdigest()[:8]
        output_filename = f"{track_info['name']} - {track_info['artist']} [{file_hash}].%(ext)s"

        # Try YT Music
        logger.info(f"Trying: ytmusicsearch1:{search_query}")
        file_path = await self._try_download_with_yt_dlp(search_query, quality, output_filename, "ytmusicsearch1")
        if file_path:
            return file_path

        # Try SoundCloud
        logger.info(f"Trying: scsearch1:{search_query}")
        file_path = await self._try_download_with_yt_dlp(search_query, quality, output_filename, "scsearch1")
        if file_path:
            return file_path

        # Try MP3Juices
        logger.info(f"Trying MP3Juices for: {search_query}")
        file_path = await self._download_from_mp3juices(search_query)
        if file_path:
            return file_path

        logger.error(f"Download failed for all sources: {search_query}")
        return None

    async def _try_download_with_yt_dlp(self, search_query: str, quality: str, output_filename: str, search_prefix: str) -> Optional[str]:
        ydl_opts = self._get_ydl_options(quality)
        ydl_opts['outtmpl'] = os.path.join(self.download_dir, output_filename)

        loop = asyncio.get_event_loop()
        try:
            return await asyncio.wait_for(loop.run_in_executor(None, self._download_audio, f"{search_prefix}:{search_query}", ydl_opts), timeout=60)
        except Exception as e:
            logger.error(f"yt-dlp download error: {e}")
            return None

    def _download_audio(self, query: str, ydl_opts: Dict) -> Optional[str]:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=True)
                path = ydl.prepare_filename(info)
                base = os.path.splitext(path)[0]
                for ext in ['.mp3', '.m4a', '.webm', '.ogg']:
                    final_path = base + ext
                    if os.path.exists(final_path):
                        return final_path
            return None
        except Exception as e:
            logger.error(f"yt-dlp download error: {e}")
            return None

    def _get_ydl_options(self, quality: str) -> Dict:
        ydl_opts = {
            'format': 'bestaudio',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'outtmpl': os.path.join(self.download_dir, '%(title)s.%(ext)s'),
        }
        return ydl_opts

    async def _download_from_mp3juices(self, query: str) -> Optional[str]:
        try:
            search_url = f"https://www.mp3juices.cc/search.php?q={requests.utils.quote(query)}"
            headers = {'User-Agent': 'Mozilla/5.0'}
            resp = requests.get(search_url, headers=headers, timeout=15)
            soup = BeautifulSoup(resp.text, 'html.parser')
            download_links = soup.select("a.button[href*='/get?']")

            if not download_links:
                logger.error("No MP3Juices links found")
                return None

            link = "https://www.mp3juices.cc" + download_links[0]['href']
            file_resp = requests.get(link, stream=True)
            if file_resp.status_code == 200:
                file_path = os.path.join(self.download_dir, f"{query}.mp3")
                with open(file_path, 'wb') as f:
                    for chunk in file_resp.iter_content(1024):
                        f.write(chunk)
                return file_path
        except Exception as e:
            logger.error(f"MP3Juices download error: {e}")
        return None