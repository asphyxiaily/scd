import subprocess
import time
import signal
from typing import Optional
from pathlib import Path


class YtDlpDownloader:
    def __init__(self, delay: float = 0.0, verbose: bool = False):
        self.delay = delay
        self.verbose = verbose
        self.current_process = None

    def download_track(self, track_url: str, output_path: Path, max_retries: int = 3) -> bool:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            'yt-dlp',
            '--extract-audio',
            '--audio-format', 'mp3',
            '--audio-quality', '0',
            '--no-playlist',
            '--no-warnings',
            '--quiet',
            '--no-progress',
            '--output', str(output_path),
            track_url
        ]

        if self.verbose:
            print(f"  [debug] running command: {' '.join(cmd)}")

        for attempt in range(max_retries):
            try:
                self.current_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                stdout, stderr = self.current_process.communicate(timeout=120)
                returncode = self.current_process.returncode
                self.current_process = None

                if self.verbose:
                    print(f"  [debug] return code: {returncode}")
                    if stdout:
                        print(f"  [debug] stdout: {stdout[:200]}")
                    if stderr:
                        print(f"  [debug] stderr: {stderr[:200]}")

                if returncode == 0:
                    if self.delay > 0:
                        time.sleep(self.delay)
                    return True
                else:
                    error_msg = stderr.strip() if stderr else "Unknown error"

                    # no retry on permanent failures
                    if any(x in error_msg for x in ['404: Not Found', 'Video unavailable', 'Private video', 'This track was not found', 'geo restriction']):
                        if self.verbose:
                            print(f"  [debug] permanent failure detected, not retrying")
                        return False

                    if attempt < max_retries - 1:
                        delay = 2.0 * (2 ** attempt)
                        if self.verbose:
                            print(f"  [debug] attempt {attempt + 1} failed: {error_msg[:100]}. retrying in {delay}s...")
                        time.sleep(delay)
                    else:
                        if self.verbose:
                            print(f"  [debug] all {max_retries} attempts failed")
                        return False

            except subprocess.TimeoutExpired:
                if self.current_process:
                    try:
                        self.current_process.kill()
                        self.current_process.wait(timeout=5)
                    except:
                        pass
                    self.current_process = None

                if self.verbose:
                    print(f"  [debug] attempt {attempt + 1} timed out")

                if attempt < max_retries - 1:
                    delay = 2.0 * (2 ** attempt)
                    time.sleep(delay)
                else:
                    return False

            except KeyboardInterrupt:
                if self.current_process:
                    try:
                        self.current_process.kill()
                        self.current_process.wait(timeout=2)
                    except:
                        pass
                    self.current_process = None
                raise

            except Exception as e:
                if self.verbose:
                    print(f"  [debug] exception: {e}")

                if self.current_process:
                    try:
                        self.current_process.kill()
                    except:
                        pass
                    self.current_process = None
                return False

            finally:
                if output_path.exists() and output_path.stat().st_size == 0:
                    if self.verbose:
                        print(f"  [debug] removing empty file: {output_path}")
                    output_path.unlink()

        return False

    def cancel(self):
        if self.current_process:
            try:
                self.current_process.kill()
                self.current_process.wait(timeout=2)
            except:
                pass
            self.current_process = None
