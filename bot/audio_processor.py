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
        ydl_opts = self._get_ydl_options(quality)

        file_hash = hashlib.md5(search_query.encode()).hexdigest()[:8]
        output_filename = f"{track_info['name']} - {track_info['artist']} [{file_hash}].%(ext)s"
        ydl_opts['outtmpl'] = os.path.join(self.download_dir, output_filename)

        sources = [
            f"scsearch1:{search_query}",
            f"ytmusicsearch1:{search_query}"
        ]

        for source in sources:
            logger.info(f"Trying: {source}")
            try:
                loop = asyncio.get_event_loop()
                file_path = await asyncio.wait_for(
                    loop.run_in_executor(None, self._download_audio, source, ydl_opts),
                    timeout=60
                )
                if file_path and os.path.exists(file_path):
                    logger.info(f"Downloaded: {file_path}")
                    return file_path
            except Exception as e:
                logger.error(f"yt-dlp download error: {e}")
        
        logger.error(f"Download failed for all sources: {search_query}")
        return None

    def _download_audio(self, search_query: str, ydl_opts: Dict) -> Optional[str]:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                result = ydl.extract_info(search_query, download=True)
                expected_path = ydl.prepare_filename(result)
                base_path = os.path.splitext(expected_path)[0]

                for ext in ['.mp3', '.m4a', '.webm', '.ogg']:
                    potential = base_path + ext
                    if os.path.exists(potential):
                        return potential

                for file in os.listdir(self.download_dir):
                    if file.startswith(os.path.basename(base_path)):
                        return os.path.join(self.download_dir, file)
                return None
        except Exception as e:
            logger.error(f"yt-dlp download error: {e}")
            return None

    def _get_ydl_options(self, quality: str) -> Dict:
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio',
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extractflat': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'writedescription': False,
            'writeinfojson': False,
            'writethumbnail': False,
            'socket_timeout': 20,
            'retries': 2,
            'fragment_retries': 2,
        }

        if quality == "128":
            ydl_opts['format'] = 'bestaudio[abr<=128]/bestaudio'
        elif quality == "192":
            ydl_opts['format'] = 'bestaudio[abr<=192]/bestaudio'
        elif quality == "320":
            ydl_opts['format'] = 'bestaudio[abr>192]/bestaudio'
        else:
            ydl_opts['format'] = 'bestaudio'

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