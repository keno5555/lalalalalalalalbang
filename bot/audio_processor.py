import os
import logging
import asyncio
import hashlib
import tempfile
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class AudioProcessor:
    def __init__(self):
        self.download_dir = tempfile.mkdtemp(prefix="music_bot_")
        logger.info(f"AudioProcessor initialized. Download dir: {self.download_dir}")

    async def download_track(self, track_info, quality):
        try:
            search_query = f"{track_info['name']} {track_info['artist']}"
            logger.info(f"Searching via Y2Mate: {search_query}")

            loop = asyncio.get_event_loop()
            file_path = await loop.run_in_executor(None, self._download_from_y2mate, search_query)
            return file_path if file_path else None

        except Exception as e:
            logger.error(f"Download error for track {track_info['name']}: {e}")
            return None

    def _download_from_y2mate(self, query):
        try:
            search_url = f"https://www.y2mate.is/mates/en68/analyze/ajax"
            headers = {
                "User-Agent": "Mozilla/5.0",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
            }

            # Search YouTube
            yt_search = f"https://www.youtube.com/results?search_query={query.replace(' ', '+')}"
            yt_html = requests.get(yt_search, headers=headers).text
            soup = BeautifulSoup(yt_html, 'html.parser')
            for script in soup.find_all("script"):
                if 'videoId' in script.text:
                    start = script.text.find('"videoId":"') + 11
                    video_id = script.text[start:start+11]
                    break
            else:
                logger.error("No YouTube video ID found from search")
                return None

            video_url = f"https://www.youtube.com/watch?v={video_id}"
            logger.info(f"Using video: {video_url}")

            # Get Y2Mate download info
            payload = {
                "url": video_url,
                "q_auto": 0,
                "ajax": 1
            }
            res = requests.post(search_url, headers=headers, data=payload).json()

            soup = BeautifulSoup(res['result'], 'html.parser')
            mp3_btn = soup.select_one("a[href*='/mates/en68/convert']")
            if not mp3_btn:
                logger.error("Y2Mate: No MP3 download link found.")
                return None

            convert_url = "https://www.y2mate.is" + mp3_btn['href']
            logger.info(f"Converting via: {convert_url}")
            res2 = requests.get(convert_url, headers=headers)
            soup2 = BeautifulSoup(res2.text, 'html.parser')
            final_btn = soup2.select_one("a[href^='https://dl']")

            if not final_btn:
                logger.error("Y2Mate: Final download link not found.")
                return None

            download_url = final_btn['href']
            logger.info(f"Downloading from: {download_url}")

            file_hash = hashlib.md5(query.encode()).hexdigest()[:8]
            filename = f"{query[:40]}_{file_hash}.mp3"
            filepath = os.path.join(self.download_dir, filename)

            r = requests.get(download_url, stream=True)
            with open(filepath, "wb") as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)

            return filepath if os.path.exists(filepath) else None

        except Exception as e:
            logger.error(f"Y2Mate download error: {e}")
            return None

    def cleanup_file(self, file_path):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to clean: {e}")

    def cleanup_all(self):
        try:
            for file in os.listdir(self.download_dir):
                self.cleanup_file(os.path.join(self.download_dir, file))
            os.rmdir(self.download_dir)
        except Exception as e:
            logger.warning(f"Cleanup all failed: {e}")
