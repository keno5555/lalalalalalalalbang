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
        ydl_opts = self._get_ydl_options(quality, track_info)

        platforms = [
            f"ytmusicsearch1:{search_query}",
            f"scsearch1:{search_query}"
        ]

        loop = asyncio.get_event_loop()

        for query in platforms:
            logger.info(f"Trying: {query}")
            try:
                file_path = await asyncio.wait_for(
                    loop.run_in_executor(None, self._download_audio, query, ydl_opts),
                    timeout=60
                )
                if file_path and os.path.exists(file_path):
                    logger.info(f"Successfully downloaded: {file_path}")
                    return file_path
            except asyncio.TimeoutError:
                logger.error(f"Timeout while downloading: {query}")
            except Exception as e:
                logger.error(f"Download error: {e}")

        logger.error(f"Download failed for all sources: {search_query}")
        return None

    def _download_audio(self, search_query: str, ydl_opts: Dict) -> Optional[str]:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=True)
                if 'entries' in info:
                    info = info['entries'][0]

                expected_path = ydl.prepare_filename(info)
                base_path = os.path.splitext(expected_path)[0]

                for ext in ['.mp3', '.m4a', '.webm', '.ogg']:
                    potential_path = base_path + ext
                    if os.path.exists(potential_path):
                        return potential_path

                for file in os.listdir(self.download_dir):
                    if file.startswith(os.path.basename(base_path)):
                        return os.path.join(self.download_dir, file)

                logger.error(f"Downloaded file not found: {search_query}")
                return None
        except Exception as e:
            logger.error(f"yt-dlp download error: {e}")
            return None

    def _get_ydl_options(self, quality: str, track_info: Dict) -> Dict:
        file_hash = hashlib.md5(f"{track_info['name']} {track_info['artist']}".encode()).hexdigest()[:8]
        output_filename = f"{track_info['name']} - {track_info['artist']} [{file_hash}].%(ext)s"

        format_quality = {
            "128": "bestaudio[abr<=128]/bestaudio",
            "192": "bestaudio[abr<=192]/bestaudio",
            "320": "bestaudio[abr>192]/bestaudio"
        }.get(quality, "bestaudio[abr<=192]/bestaudio")

        return {
            'format': format_quality,
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extractflat': False,
            'writesubtitles': False,
            'writethumbnail': True,
            'embed-thumbnail': True,
            'add-metadata': True,
            'outtmpl': os.path.join(self.download_dir, output_filename),
            'socket_timeout': 15,
            'retries': 2,
            'fragment_retries': 2,
            'postprocessors': [
                {
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'mp3',
                    'preferredquality': '192'
                },
                {
                    'key': 'EmbedThumbnail'
                },
                {
                    'key': 'FFmpegMetadata'
                }
            ]
        }

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
                self.cleanup_file(os.path.join(self.download_dir, file))
            os.rmdir(self.download_dir)
            logger.info("All files cleaned up successfully")
        except Exception as e:
            logger.warning(f"Failed to cleanup all files: {e}")