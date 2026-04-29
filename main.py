#!/usr/bin/env python3
import argparse
import sys
import signal
from pathlib import Path
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

from soundcloud_scraper import SoundCloudScraper
from cobalt_downloader import YtDlpDownloader
from metadata_tagger import MetadataTagger
from progress_tracker import ProgressTracker


# ANSI CC
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    DIM = '\033[2m'


shutdown_flag = threading.Event()


def signal_handler(signum, frame):
    print(f"\n\n{Colors.YELLOW}⚠ interrupt received, finishing current downloads...{Colors.ENDC}")
    print(f"{Colors.DIM}press ctrl+c again to force quit{Colors.ENDC}\n")
    shutdown_flag.set()
    signal.signal(signal.SIGINT, signal.SIG_DFL)


def main():
    parser = argparse.ArgumentParser(
        description='batch download soundcloud tracks with metadata and artworks',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f'''
{Colors.BOLD}examples:{Colors.ENDC}
  python main.py yourusername
  python main.py https://soundcloud.com/yourusername
  python main.py https://soundcloud.com/yourusername/sets/playlist-name
  python main.py yourusername -o ./music --workers 8
  python main.py yourusername --resume
  python main.py yourusername --reset --verbose

{Colors.BOLD}tips:{Colors.ENDC}
  • use --workers 8 for faster downloads (default: 4)
  • use --resume to continue interrupted downloads
  • use --verbose to see detailed debug information
  • press ctrl+c once to stop gracefully
  • supports both user likes and playlists
        '''
    )

    parser.add_argument('username', help='soundcloud username, profile url, or playlist url')
    parser.add_argument('-o', '--output-dir', default='./downloads', help='output directory (default: ./downloads)')
    parser.add_argument('-r', '--max-retries', type=int, default=3, help='max retry attempts per track (default: 3)')
    parser.add_argument('-d', '--delay', type=float, default=0.5, help='delay between requests in seconds (default: 0.5)')
    parser.add_argument('-w', '--workers', type=int, default=4, help='number of parallel downloads (default: 4)')
    parser.add_argument('--resume', action='store_true', help='resume from previous download')
    parser.add_argument('--reset', action='store_true', help='clear progress and start fresh')
    parser.add_argument('-v', '--verbose', action='store_true', help='show detailed debug information')

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    progress_file = output_dir / '.sc_download_progress.json'
    tracker = ProgressTracker(str(progress_file))

    if args.reset:
        print(f"{Colors.YELLOW}resetting progress...{Colors.ENDC}")
        tracker.reset()

    if args.resume or progress_file.exists():
        print(f"{Colors.CYAN}loading previous progress...{Colors.ENDC}")
        tracker.load_progress()
    else:
        tracker.load_progress()

    print(r" _______  _______ _____  ")
    print(r" |______ |       |     \ ")
    print(r" ______| |______ |_____/ ")
    print(r" ")

    # graceful shutdown LMAO
    signal.signal(signal.SIGINT, signal_handler)

    scraper = SoundCloudScraper(delay=2.0)
    downloader = YtDlpDownloader(delay=args.delay)
    tagger = MetadataTagger()

    print(f"{Colors.CYAN}step 1: fetching tracks from soundcloud...{Colors.ENDC}")
    tracks = scraper.get_liked_tracks(args.username)

    if not tracks:
        print(f"\n{Colors.RED}no tracks found. check the username/url and try again.{Colors.ENDC}")
        sys.exit(1)

    tracks_to_download = [t for t in tracks if not tracker.is_completed(t.track_id)]

    if not tracks_to_download:
        print(f"\n{Colors.GREEN}all tracks already downloaded!{Colors.ENDC}")
        sys.exit(0)

    print(f"\n{Colors.CYAN}step 2: downloading {Colors.BOLD}{len(tracks_to_download)}{Colors.ENDC}{Colors.CYAN} tracks...{Colors.ENDC}")
    print(f"{Colors.DIM}  (skipping {len(tracks) - len(tracks_to_download)} already completed)")
    print(f"  using {args.workers} parallel workers{Colors.ENDC}\n")

    tracker.set_pending([t.track_id for t in tracks_to_download])

    success_count = 0
    failed_count = 0
    unavailable_count = 0
    lock = threading.Lock()
    active_downloaders = []
    worker_tagger = MetadataTagger()

    def download_track_worker(track):
        nonlocal success_count, failed_count, unavailable_count

        if shutdown_flag.is_set():
            return None, track, "interrupted"

        worker_downloader = YtDlpDownloader(delay=args.delay, verbose=args.verbose)
        active_downloaders.append(worker_downloader)

        try:
            if args.verbose:
                pbar.write(f"{Colors.DIM}[debug] starting download: {track.artist} - {track.title}{Colors.ENDC}")
                pbar.write(f"{Colors.DIM}[debug] url: {track.url}{Colors.ENDC}")

            filename = worker_tagger.create_filename(track.artist, track.title)
            temp_path = output_dir / f"temp_{track.track_id}.mp3"
            final_path = output_dir / filename

            if args.verbose:
                pbar.write(f"{Colors.DIM}[debug] temp file: {temp_path}{Colors.ENDC}")
                pbar.write(f"{Colors.DIM}[debug] final file: {final_path}{Colors.ENDC}")

            download_success = worker_downloader.download_track(track.url, temp_path, max_retries=args.max_retries)

            if not download_success:
                raise Exception("Download failed")

            if args.verbose:
                pbar.write(f"{Colors.DIM}[debug] tagging metadata...{Colors.ENDC}")

            worker_tagger.tag_file(temp_path, track.title, track.artist, track.artwork_url)

            temp_path.rename(final_path)

            with lock:
                tracker.mark_completed(track.track_id)
                success_count += 1

            if args.verbose:
                pbar.write(f"{Colors.GREEN}✓ {track.artist} - {track.title}{Colors.ENDC}")

            return True, track, None

        except KeyboardInterrupt:
            return None, track, "interrupted"

        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()

            error_msg = str(e)

            is_unavailable = any(x in error_msg for x in ['404', 'unavailable', 'not found', 'geo restriction', 'Private'])

            # the fuck am i even doing here

            with lock:
                tracker.mark_failed(track.track_id, error_msg)
                if is_unavailable:
                    unavailable_count += 1
                    if args.verbose:
                        pbar.write(f"{Colors.YELLOW}⚠ unavailable: {track.artist} - {track.title}{Colors.ENDC}")
                else:
                    failed_count += 1
                    if args.verbose:
                        pbar.write(f"{Colors.RED}✗ failed: {track.artist} - {track.title}: {error_msg[:80]}{Colors.ENDC}")

            return False, track, error_msg

        finally:
            if worker_downloader in active_downloaders:
                active_downloaders.remove(worker_downloader)

    with tqdm(total=len(tracks_to_download), desc="downloading", unit="track", smoothing=0.1, ncols=80, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]') as pbar:
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(download_track_worker, track): track for track in tracks_to_download}

            for future in as_completed(futures):
                if shutdown_flag.is_set():
                    pbar.write(f"\n{Colors.YELLOW}stopping downloads...{Colors.ENDC}")

                    for downloader in active_downloaders[:]:
                        downloader.cancel()

                    for f in futures:
                        f.cancel()

                    break

                track = futures[future]
                try:
                    result = future.result()
                    if result is None:
                        continue

                    success, track_obj, error = result

                except Exception as e:
                    if args.verbose:
                        pbar.write(f"{Colors.RED}✗ exception: {track.artist} - {track.title}: {str(e)[:60]}{Colors.ENDC}")
                    with lock:
                        tracker.mark_failed(track.track_id, str(e))
                        failed_count += 1

                pbar.update(1)

    print(f"\n{Colors.BOLD}{'='*60}")
    print("download summary")
    print(f"{'='*60}{Colors.ENDC}")
    print(f"  total tracks:          {Colors.BOLD}{len(tracks)}{Colors.ENDC}")
    print(f"  {Colors.GREEN}successfully downloaded: {success_count}{Colors.ENDC}")
    print(f"  {Colors.YELLOW}unavailable:           {unavailable_count}{Colors.ENDC} {Colors.DIM}(deleted/private/region-locked){Colors.ENDC}")
    print(f"  {Colors.RED}failed:                {failed_count}{Colors.ENDC}")
    print(f"  {Colors.DIM}already completed:     {len(tracks) - len(tracks_to_download)}{Colors.ENDC}")
    print(f"\n{Colors.CYAN}files saved to: {output_dir.absolute()}{Colors.ENDC}")

    if failed_count > 0:
        print(f"\n{Colors.YELLOW}  to retry failed downloads, run with --resume flag{Colors.ENDC}")

    print(f"{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

if __name__ == '__main__':
    main()
