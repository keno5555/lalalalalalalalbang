import os
import logging
import asyncio
import yt_dlp
from typing import Dict, Optional
import tempfile
import requests
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TIT2, TPE1, TALB

logger = logging.getLogger(__name__)

class AudioProcessor:
    def __init__(self):
        self.download_dir = tempfile.mkdtemp(prefix="music_bot_")
        logger.info(f"Audio processor initialized with download directory: {self.download_dir}")

    async def download_track(self, track_info: Dict, quality: str) -> Optional[str]:
        search_query = f"{track_info['name']} {track_info['artist']}"
        sources = [
            f"ytmusicsearch1:{search_query}",
            f"scsearch1:{search_query}",
            f"ytsearch1:{search_query}",
        ]

        for source in sources:
            try:
                logger.info(f"Trying: {source}")
                ydl_opts = self._get_ydl_options(quality)
                output_path = os.path.join(self.download_dir, f"{track_info['name']} - {track_info['artist']}.%(ext)s")
                ydl_opts['outtmpl'] = output_path

                loop = asyncio.get_event_loop()
                file_path = await asyncio.wait_for(
                    loop.run_in_executor(None, self._download_audio, source, ydl_opts),
                    timeout=60
                )

                if file_path and os.path.exists(file_path):
                    logger.info(f"Downloaded file: {file_path}")
                    self._embed_metadata(file_path, track_info, track_info.get("cover_url"))
                    return file_path
            except asyncio.TimeoutError:
                logger.warning(f"Timeout: {source}")
            except Exception as e:
                logger.error(f"Download error from {source}: {e}")

        logger.error(f"Download failed for all sources: {search_query}")
        return None

    def _download_audio(self, query: str, ydl_opts: Dict) -> Optional[str]:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(query, download=False)
                if 'entries' not in info or not info['entries']:
                    return None

                video_info = info['entries'][0]
                video_url = video_info['url']
                ydl.download([video_url])
                expected_path = ydl.prepare_filename(video_info)

                base_path = os.path.splitext(expected_path)[0]
                for ext in ['.mp3', '.m4a', '.webm', '.ogg']:
                    full_path = base_path + ext
                    if os.path.exists(full_path):
                        return full_path

                for f in os.listdir(self.download_dir):
                    if f.startswith(os.path.basename(base_path)):
                        return os.path.join(self.download_dir, f)
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
            'outtmpl': None,  # Will be set later
            'socket_timeout': 20,
            'retries': 2,
            'fragment_retries': 2,
            'cookiesfrombrowser': ('chrome',),  # Optional: to help with YouTube blocking
        }

        if quality == "128":
            ydl_opts['format'] = 'bestaudio[abr<=128]/bestaudio'
        elif quality == "192":
            ydl_opts['format'] = 'bestaudio[abr<=192]/bestaudio'
        elif quality == "320":
            ydl_opts['format'] = 'bestaudio/best'

        return ydl_opts

    def _embed_metadata(self, file_path: str, track_info: Dict, cover_url: Optional[str]):
        try:
            audio = MP3(file_path, ID3=ID3)
            try:
                audio.add_tags()
            except Exception:
                pass

            audio["TIT2"] = TIT2(encoding=3, text=track_info.get("name", ""))
            audio["TPE1"] = TPE1(encoding=3, text=track_info.get("artist", ""))
            audio["TALB"] = TALB(encoding=3, text=track_info.get("album", ""))

            if cover_url:
                response = requests.get(cover_url)
                if response.ok:
                    audio["APIC"] = APIC(
                        encoding=3,
                        mime="image/jpeg",
                        type=3,
                        desc="Cover",
                        data=response.content
                    )
            audio.save()
            logger.info("Metadata embedded successfully.")
        except Exception as e:
            logger.warning(f"Failed to embed metadata: {e}")

    def cleanup_file(self, file_path: str):
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"File deleted: {file_path}")
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")

    def cleanup_all(self):
        try:
            for f in os.listdir(self.download_dir):
                self.cleanup_file(os.path.join(self.download_dir, f))
            os.rmdir(self.download_dir)
        except Exception as e:
            logger.warning(f"Failed to cleanup all files: {e}")