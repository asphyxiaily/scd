# scd

just a thing i made to batch download sc tracks in the simplest way possible.

## what it does

take a wild guess

## install

```bash
git clone https://github.com/asphyxiaily/scd.git
cd scd
pip install -r requirements.txt
pip install yt-dlp
```

## use

```bash
# basic
python main.py yourusername

# playlist
python main.py https://soundcloud.com/yourusername/sets/playlist-name

# faster
python main.py yourusername --workers 8

# resume
python main.py yourusername --resume
```

## options

```
-o, --output-dir      where to save (default: ./downloads)
-w, --workers         parallel downloads (default: 4)
-r, --max-retries     retry attempts (default: 3)
-d, --delay           delay between requests (default: 0.5s)
--resume              continue from where you stopped
--reset               start fresh
-v, --verbose         debug info
```

## speed

for ~2500 tracks:
- 4 workers: ~1.5 hours
- 8 workers: ~45 min
- 16 workers: ~30 min

## problems

**"no tracks found"**
- check the username
- try using a vpn if possible

**"yt-dlp not found"**
```bash
pip install yt-dlp
```

**slow downloads**
```bash
python main.py yourusername --workers 8
```
(or use higher values)

**getting rate limited**
```bash
python main.py yourusername --workers 2 --delay 2
```

**lots of unavailable tracks**
- yeah that's normal, tracks get deleted
- usually 5-10% are gone

## building

```bash
# windows
pip install pyinstaller
build_windows.bat

# linux
pip install pyinstaller
./build_linux.sh
```

see [BUILD.md](BUILD.md) for details

## how it works

1. scrapes soundcloud api
2. downloads with yt-dlp
3. adds metadata and artwork
4. saves progress

## notes

- only public likes/playlists
- downloads as 320kbps mp3
- saves as "artist - title.mp3"
- for personal use only

## credits

- [yt-dlp](https://github.com/yt-dlp/yt-dlp)
- [mutagen](https://github.com/quodlibet/mutagen)
- [tqdm](https://github.com/tqdm/tqdm)
