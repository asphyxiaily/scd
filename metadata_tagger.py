import re
import requests
from pathlib import Path
from typing import Optional
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, TIT2, TPE1, APIC, ID3NoHeaderError


def sanitize_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', ' ', name)
    name = name.strip('. ')

    if len(name) > 200:
        name = name[:200]

    return name or 'untitled'


class MetadataTagger:
    def __init__(self):
        self.session = requests.Session()

    def download_artwork(self, url: str) -> Optional[bytes]:
        if not url:
            return None

        # multi-res
        url_variants = [
            url.replace('-large', '-t500x500'),
            url.replace('-large', '-t300x300'),
            url.replace('-t500x500', '-t300x300'),
            url,
        ]

        # duplicates or sum bullshit
        seen = set()
        url_variants = [x for x in url_variants if not (x in seen or seen.add(x))]

        for variant_url in url_variants:
            try:
                response = self.session.get(variant_url, timeout=10)
                if response.status_code == 200 and len(response.content) > 0:
                    return response.content
            except:
                continue

        return None

    def embed_artwork(self, file_path: Path, image_data: bytes) -> bool:
        if not image_data:
            return False

        try:
            audio = MP3(file_path, ID3=ID3)

            if audio.tags is None:
                audio.add_tags()

            mime_type = 'image/jpeg'
            if image_data[:4] == b'\x89PNG':
                mime_type = 'image/png'

            audio.tags.add(
                APIC(
                    encoding=3,
                    mime=mime_type,
                    type=3,
                    desc='Cover',
                    data=image_data
                )
            )

            audio.save()
            return True
        except Exception as e:
            print(f"  warning: could not embed artwork: {e}")
            return False

    def tag_file(self, file_path: Path, title: str, artist: str, artwork_url: Optional[str] = None) -> bool:
        if not file_path.exists():
            print(f"  error: file does not exist: {file_path}")
            return False

        try:
            try:
                audio = MP3(file_path, ID3=ID3)
            except ID3NoHeaderError:
                audio = MP3(file_path)
                audio.add_tags()

            if audio.tags is None:
                audio.add_tags()

            audio.tags.add(TIT2(encoding=3, text=title))
            audio.tags.add(TPE1(encoding=3, text=artist))

            audio.save()

            if artwork_url:
                image_data = self.download_artwork(artwork_url)
                if image_data:
                    self.embed_artwork(file_path, image_data)

            return True
        except Exception as e:
            print(f"  error tagging file: {e}")
            return False

    def create_filename(self, artist: str, title: str) -> str:
        artist_clean = sanitize_filename(artist)
        title_clean = sanitize_filename(title)
        return f"{artist_clean} - {title_clean}.mp3"
