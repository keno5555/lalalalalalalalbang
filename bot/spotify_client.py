import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import logging
import asyncio
from typing import Dict, List, Optional
from config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET

logger = logging.getLogger(__name__)

class SpotifyClient:
    def __init__(self):
        try:
            client_credentials_manager = SpotifyClientCredentials(
                client_id=SPOTIFY_CLIENT_ID,
                client_secret=SPOTIFY_CLIENT_SECRET
            )
            self.sp = spotipy.Spotify(
                client_credentials_manager=client_credentials_manager,
                requests_timeout=15,  # Increased timeout from default
                retries=3
            )
            logger.info("Spotify client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Spotify client: {e}")
            self.sp = None

    async def get_track_info(self, track_id: str) -> Optional[Dict]:
        if not self.sp:
            logger.error("Spotify client not initialized")
            return None

        try:
            loop = asyncio.get_event_loop()
            track = await loop.run_in_executor(None, self.sp.track, track_id)
            return {
                'id': track['id'],
                'name': track['name'],
                'artist': ', '.join(artist['name'] for artist in track['artists']),
                'album': track['album']['name'],
                'duration': self._format_duration(track['duration_ms']),
                'duration_ms': track['duration_ms'],
                'popularity': track['popularity'],
                'preview_url': track.get('preview_url'),
                'external_urls': track['external_urls'],
                'release_date': track['album']['release_date'],
                'image_url': track['album']['images'][0]['url'] if track['album']['images'] else None
            }
        except Exception as e:
            logger.error(f"Error retrieving track info for {track_id}: {e}")
            return None

    async def get_playlist_info(self, playlist_id: str) -> Optional[Dict]:
        if not self.sp:
            logger.error("Spotify client not initialized")
            return None

        try:
            loop = asyncio.get_event_loop()
            playlist = await loop.run_in_executor(None, self.sp.playlist, playlist_id)
            tracks = []
            results = playlist['tracks']

            while results:
                for item in results['items']:
                    if item['track'] and item['track']['type'] == 'track':
                        track = item['track']
                        tracks.append({
                            'id': track['id'],
                            'name': track['name'],
                            'artist': ', '.join(artist['name'] for artist in track['artists']),
                            'album': track['album']['name'],
                            'duration': self._format_duration(track['duration_ms']),
                            'duration_ms': track['duration_ms'],
                            'popularity': track['popularity']
                        })

                if results['next']:
                    results = await loop.run_in_executor(None, self.sp.next, results)
                else:
                    results = None

            return {
                'id': playlist['id'],
                'name': playlist['name'],
                'description': playlist.get('description', ''),
                'owner': playlist['owner']['display_name'],
                'tracks': tracks,
                'total_tracks': len(tracks),
                'followers': playlist['followers']['total'],
                'image_url': playlist['images'][0]['url'] if playlist['images'] else None
            }

        except Exception as e:
            logger.error(f"Error retrieving playlist info for {playlist_id}: {e}")
            return None

    async def get_album_info(self, album_id: str) -> Optional[Dict]:
        if not self.sp:
            logger.error("Spotify client not initialized")
            return None

        try:
            loop = asyncio.get_event_loop()
            album = await loop.run_in_executor(None, self.sp.album, album_id)
            tracks = []

            for track in album['tracks']['items']:
                tracks.append({
                    'id': track['id'],
                    'name': track['name'],
                    'artist': ', '.join(artist['name'] for artist in track['artists']),
                    'album': album['name'],
                    'duration': self._format_duration(track['duration_ms']),
                    'duration_ms': track['duration_ms'],
                    'track_number': track['track_number']
                })

            return {
                'id': album['id'],
                'name': album['name'],
                'artist': ', '.join(artist['name'] for artist in album['artists']),
                'tracks': tracks,
                'total_tracks': album['total_tracks'],
                'release_date': album['release_date'],
                'genres': album.get('genres', []),
                'popularity': album['popularity'],
                'image_url': album['images'][0]['url'] if album['images'] else None
            }

        except Exception as e:
            logger.error(f"Error retrieving album info for {album_id}: {e}")
            return None

    async def search_track(self, query: str, limit: int = 10) -> List[Dict]:
        if not self.sp:
            logger.error("Spotify client not initialized")
            return []

        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self.sp.search(q=query, type='track', limit=limit)
            )

            return [{
                'id': t['id'],
                'name': t['name'],
                'artist': ', '.join(artist['name'] for artist in t['artists']),
                'album': t['album']['name'],
                'duration': self._format_duration(t['duration_ms']),
                'duration_ms': t['duration_ms'],
                'popularity': t['popularity'],
                'external_urls': t['external_urls']
            } for t in results['tracks']['items']]

        except Exception as e:
            logger.error(f"Error searching tracks for query '{query}': {e}")
            return []

    def _format_duration(self, duration_ms: int) -> str:
        seconds = duration_ms // 1000
        minutes = seconds // 60
        return f"{minutes}:{seconds % 60:02d}"