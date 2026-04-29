import requests
import re
import time
import json
from typing import List, Dict, Optional
from bs4 import BeautifulSoup
from dataclasses import dataclass


@dataclass
class TrackMetadata:
    track_id: str
    url: str
    title: str
    artist: str
    artwork_url: Optional[str] = None


class SoundCloudScraper:
    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        self.client_id = None

    def normalize_url(self, username_or_url: str) -> tuple[str, str]:
        if username_or_url.startswith('http://') or username_or_url.startswith('https://'):
            url = username_or_url.rstrip('/')

            if '/sets/' in url:
                return url, 'playlist'

            if not url.endswith('/likes'):
                url += '/likes'
            return url, 'likes'
        else:
            username = username_or_url.strip().lstrip('@')
            return f"https://soundcloud.com/{username}/likes", 'likes'

    def extract_track_id(self, url: str) -> str:
        match = re.search(r'/([^/]+)/([^/?]+)', url)
        if match:
            return f"{match.group(1)}_{match.group(2)}"
        return url

    def extract_client_id(self, html: str) -> Optional[str]:
        script_urls = re.findall(r'<script[^>]+src="([^"]+)"', html)

        for script_url in script_urls:
            if 'sndcdn.com' in script_url and script_url.endswith('.js'):
                try:
                    response = self.session.get(script_url, timeout=10)
                    client_id_match = re.search(r'client_id[=:]"([a-zA-Z0-9]+)"', response.text)
                    if client_id_match:
                        return client_id_match.group(1)
                except:
                    continue

        return None

    def get_user_id(self, username: str) -> Optional[int]:
        if not self.client_id:
            return None

        try:
            url = f"https://api-v2.soundcloud.com/resolve?url=https://soundcloud.com/{username}&client_id={self.client_id}"
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            data = response.json()
            return data.get('id')
        except Exception as e:
            print(f"  error getting user id: {e}")
            return None

    def fetch_likes_api(self, user_id: int, limit: int = 50) -> List[TrackMetadata]:
        all_tracks = []
        next_href = f"https://api-v2.soundcloud.com/users/{user_id}/likes?client_id={self.client_id}&limit={limit}&offset=0"

        page = 0
        while next_href:
            try:
                response = self.session.get(next_href, timeout=30)
                response.raise_for_status()
                data = response.json()

                collection = data.get('collection', [])
                page += 1
                print(f"  fetching page {page}: {len(collection)} items")

                for item in collection:
                    track_data = item.get('track')
                    if track_data and track_data.get('kind') == 'track':
                        track_url = track_data.get('permalink_url')
                        if track_url:
                            artwork = track_data.get('artwork_url')
                            if artwork:
                                artwork = artwork.replace('-large', '-t500x500')

                            track = TrackMetadata(
                                track_id=str(track_data.get('id', self.extract_track_id(track_url))),
                                url=track_url,
                                title=track_data.get('title', 'Unknown Title'),
                                artist=track_data.get('user', {}).get('username', 'Unknown Artist'),
                                artwork_url=artwork
                            )
                            all_tracks.append(track)

                next_href = data.get('next_href')
                if next_href and self.client_id not in next_href:
                    next_href += f"&client_id={self.client_id}"

                time.sleep(self.delay)

            except Exception as e:
                print(f"  error fetching page {page}: {e}")
                break

        return all_tracks

    def fetch_playlist_tracks(self, playlist_url: str) -> List[TrackMetadata]:
        all_tracks = []

        try:
            response = self.session.get(playlist_url, timeout=30)
            response.raise_for_status()

            if not self.client_id:
                self.client_id = self.extract_client_id(response.text)

            if not self.client_id:
                print("  error: could not extract client id")
                return []

            resolve_url = f"https://api-v2.soundcloud.com/resolve?url={playlist_url}&client_id={self.client_id}"
            response = self.session.get(resolve_url, timeout=15)
            response.raise_for_status()
            playlist_data = response.json()

            playlist_id = playlist_data.get('id')
            if not playlist_id:
                print("  error: could not get playlist id")
                return []

            print(f"  playlist: {playlist_data.get('title', 'unknown')}")
            print(f"  by: {playlist_data.get('user', {}).get('username', 'unknown')}")

            # Fetch playlist tracks
            tracks_url = f"https://api-v2.soundcloud.com/playlists/{playlist_id}?client_id={self.client_id}"
            response = self.session.get(tracks_url, timeout=30)
            response.raise_for_status()
            data = response.json()

            tracks = data.get('tracks', [])
            print(f"  found {len(tracks)} tracks in playlist")

            for track_data in tracks:
                if track_data and track_data.get('kind') == 'track':
                    track_url = track_data.get('permalink_url')
                    if track_url:
                        artwork = track_data.get('artwork_url')
                        if artwork:
                            artwork = artwork.replace('-large', '-t500x500')

                        track = TrackMetadata(
                            track_id=str(track_data.get('id', self.extract_track_id(track_url))),
                            url=track_url,
                            title=track_data.get('title', 'Unknown Title'),
                            artist=track_data.get('user', {}).get('username', 'Unknown Artist'),
                            artwork_url=artwork
                        )
                        all_tracks.append(track)

            time.sleep(self.delay)

        except Exception as e:
            print(f"  error fetching playlist: {e}")
            return []

        return all_tracks

    def get_liked_tracks(self, username_or_url: str) -> List[TrackMetadata]:
        url, url_type = self.normalize_url(username_or_url)

        if url_type == 'playlist':
            print(f"fetching playlist from: {url}")
            return self.fetch_playlist_tracks(url)

        print(f"fetching liked tracks from: {url}")

        username = username_or_url.split('/')[-1] if '/' in username_or_url else username_or_url
        username = username.strip().lstrip('@')

        try:
            print("  extracting client id...")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            self.client_id = self.extract_client_id(response.text)

            if not self.client_id:
                print("  warning: could not extract client id, falling back to basic scraping")
                return []

            print(f"  client id found: {self.client_id[:10]}...")

            print("  getting user id...")
            user_id = self.get_user_id(username)

            if not user_id:
                print("  error: could not get user id")
                return []

            print(f"  user id: {user_id}")
            print("  fetching all liked tracks via api...")

            tracks = self.fetch_likes_api(user_id)

            print(f"\ntotal tracks found: {len(tracks)}")
            return tracks

        except requests.exceptions.RequestException as e:
            print(f"error: {e}")
            return []
