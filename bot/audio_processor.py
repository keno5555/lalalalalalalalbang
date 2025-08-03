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
        try:
            search_query = f"{track_info['name']} {track_info['artist']}"
            logger.info(f"Searching for: {search_query}")
            
            ydl_opts = self._get_ydl_options(quality)

            file_hash = hashlib.md5(search_query.encode()).hexdigest()[:8]
            output_filename = f"{track_info['name']} - {track_info['artist']} [{file_hash}].%(ext)s"
            ydl_opts['outtmpl'] = os.path.join(self.download_dir, output_filename)
            
            loop = asyncio.get_event_loop()
            try:
                file_path = await asyncio.wait_for(
                    loop.run_in_executor(None, self._download_audio, search_query, ydl_opts),
                    timeout=60
                )

                if file_path and os.path.exists(file_path):
                    logger.info(f"Successfully downloaded: {file_path}")
                    return file_path
                else:
                    logger.error(f"Download failed for: {search_query}")
                    return None

            except asyncio.TimeoutError:
                logger.error(f"Download timeout for: {search_query}")
                return None

        except Exception as e:
            logger.error(f"Error downloading track {track_info['name']}: {e}")
            return None

    def _download_audio(self, search_query: str, ydl_opts: Dict) -> Optional[str]:
        sources = [
            ("ytmusic", f"ytmusicsearch1:{search_query}"),
            ("soundcloud", f"scsearch1:{search_query}"),
            ("youtube", f"ytsearch1:{search_query}")
        ]

        for source_name, query in sources:
            try:
                logger.info(f"Trying {source_name} for: {search_query}")
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    results = ydl.extract_info(query, download=False)
                    if not results or "entries" not in results or not results["entries"]:
                        continue

                    video = results["entries"][0]
                    ydl.download([video["webpage_url"]])

                    expected_path = ydl.prepare_filename(video)
                    base_path = os.path.splitext(expected_path)[0]

                    for ext in ['.mp3', '.m4a', '.webm', '.ogg']:
                        potential_path = base_path + ext
                        if os.path.exists(potential_path):
                            return potential_path

                    # fallback if format changed
                    for file in os.listdir(self.download_dir):
                        if file.startswith(os.path.basename(base_path)):
                            return os.path.join(self.download_dir, file)

            except Exception as e:
                logger.warning(f"{source_name} failed: {e}")
                continue

        logger.error(f"All sources failed for: {search_query}")
        return None

    def _get_ydl_options(self, quality: str) -> Dict:
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extractflat': False,
            'socket_timeout': 20,
            'http_chunk_size': 10485760,
            'retries': 3,
            'fragment_retries': 3,
            'cookiefile': os.path.join(os.path.dirname(__file__), 'cookies.txt'),
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'headers': {
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': '*/*',
                'Connection': 'keep-alive',
            }
        }

        if quality == "128":
            ydl_opts['format'] = 'bestaudio[abr<=128]/bestaudio'
        elif quality == "192":
            ydl_opts['format'] = 'bestaudio[abr<=192]/bestaudio'
        elif quality == "320":
            ydl_opts['format'] = 'bestaudio/best'

        return ydl_opts

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