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
        """Initialize audio processor."""
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
            # Create search query
            search_query = f"{track_info['name']} {track_info['artist']}"
            logger.info(f"Searching for: {search_query}")
            
            # Configure yt-dlp options
            ydl_opts = self._get_ydl_options(quality)
            
            # Generate unique filename
            file_hash = hashlib.md5(search_query.encode()).hexdigest()[:8]
            output_filename = f"{track_info['name']} - {track_info['artist']} [{file_hash}].%(ext)s"
            ydl_opts['outtmpl'] = os.path.join(self.download_dir, output_filename)
            
            # Search and download with timeout
            loop = asyncio.get_event_loop()
            try:
                file_path = await asyncio.wait_for(
                    loop.run_in_executor(
                        None, 
                        self._download_audio, 
                        search_query, 
                        ydl_opts
                    ),
                    timeout=60  # 1 minute timeout
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
                # Search for the track
                search_results = ydl.extract_info(
                    f"ytsearch1:{search_query}",
                    download=False
                )
                
                if not search_results or 'entries' not in search_results or not search_results['entries']:
                    logger.error(f"No search results found for: {search_query}")
                    return None
                
                # Get the first result
                video_info = search_results['entries'][0]
                video_url = video_info['url']
                
                # Download the audio
                ydl.download([video_url])
                
                # Find the downloaded file
                expected_path = ydl.prepare_filename(video_info)
                
                # yt-dlp might change the extension, so find the actual file
                base_path = os.path.splitext(expected_path)[0]
                for ext in ['.mp3', '.m4a', '.webm', '.ogg']:
                    potential_path = base_path + ext
                    if os.path.exists(potential_path):
                        return potential_path
                
                # If exact match not found, look in download directory
                for file in os.listdir(self.download_dir):
                    if file.startswith(os.path.basename(base_path)):
                        return os.path.join(self.download_dir, file)
                
                logger.error(f"Downloaded file not found for: {search_query}")
                return None
                
        except Exception as e:
            logger.error(f"yt-dlp download error: {e}")
            return None
    
    def _get_ydl_options(self, quality: str) -> Dict:
        """
        Get yt-dlp options based on quality preference.
        
        Args:
            quality: Quality setting (128, 192, 320)
            
        Returns:
            yt-dlp options dictionary
        """
        # Base options optimized for speed and reliability
        ydl_opts = {
            'format': 'bestaudio[ext=m4a]/bestaudio[ext=webm]/bestaudio',
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
            'http_chunk_size': 10485760,  # 10 MB chunks
            'retries': 2,
            'fragment_retries': 2,
        }
        
        # Skip post-processing for faster downloads - send raw audio
        # Quality selection will be handled by format selection instead
        if quality == "128":
            ydl_opts['format'] = 'bestaudio[abr<=128]/bestaudio'
        elif quality == "192":
            ydl_opts['format'] = 'bestaudio[abr<=192]/bestaudio'  
        elif quality == "320":
            ydl_opts['format'] = 'bestaudio/best'
        else:
            ydl_opts['format'] = 'bestaudio[abr<=192]/bestaudio'
        
        return ydl_opts
    
    def cleanup_file(self, file_path: str):
        """
        Clean up downloaded file.
        
        Args:
            file_path: Path to file to be cleaned up
        """
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"Cleaned up file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup file {file_path}: {e}")
    
    def cleanup_all(self):
        """Clean up all downloaded files."""
        try:
            for file in os.listdir(self.download_dir):
                file_path = os.path.join(self.download_dir, file)
                self.cleanup_file(file_path)
            os.rmdir(self.download_dir)
            logger.info("All files cleaned up successfully")
        except Exception as e:
            logger.warning(f"Failed to cleanup all files: {e}")
