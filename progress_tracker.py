import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class FailedTrack:
    track_id: str
    error: str
    attempts: int


@dataclass
class ProgressState:
    completed: List[str]
    failed: List[FailedTrack]
    pending: List[str]
    last_updated: str

    def to_dict(self):
        return {
            'completed': self.completed,
            'failed': [asdict(f) for f in self.failed],
            'pending': self.pending,
            'last_updated': self.last_updated
        }

    @classmethod
    def from_dict(cls, data: dict):
        failed = [FailedTrack(**f) for f in data.get('failed', [])]
        return cls(
            completed=data.get('completed', []),
            failed=failed,
            pending=data.get('pending', []),
            last_updated=data.get('last_updated', '')
        )


class ProgressTracker:
    def __init__(self, progress_file: str = '.sc_download_progress.json'):
        self.progress_file = progress_file
        self.state: Optional[ProgressState] = None

    def load_progress(self) -> ProgressState:
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.state = ProgressState.from_dict(data)
                    return self.state
            except (json.JSONDecodeError, IOError) as e:
                print(f"warning: could not load progress file: {e}")

        self.state = ProgressState(
            completed=[],
            failed=[],
            pending=[],
            last_updated=datetime.utcnow().isoformat() + 'Z'
        )
        return self.state

    def save_progress(self) -> bool:
        if self.state is None:
            return False

        try:
            self.state.last_updated = datetime.utcnow().isoformat() + 'Z'
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(self.state.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except IOError as e:
            print(f"error saving progress: {e}")
            return False

    def mark_completed(self, track_id: str):
        if self.state is None:
            self.load_progress()

        if track_id not in self.state.completed:
            self.state.completed.append(track_id)

        if track_id in self.state.pending:
            self.state.pending.remove(track_id)

        self.state.failed = [f for f in self.state.failed if f.track_id != track_id]
        self.save_progress()

    def mark_failed(self, track_id: str, error: str):
        if self.state is None:
            self.load_progress()

        existing = next((f for f in self.state.failed if f.track_id == track_id), None)

        if existing:
            existing.attempts += 1
            existing.error = error
        else:
            self.state.failed.append(FailedTrack(
                track_id=track_id,
                error=error,
                attempts=1
            ))

        if track_id in self.state.pending:
            self.state.pending.remove(track_id)

        self.save_progress()

    def is_completed(self, track_id: str) -> bool:
        if self.state is None:
            self.load_progress()
        return track_id in self.state.completed

    def get_failed_count(self, track_id: str) -> int:
        if self.state is None:
            self.load_progress()

        failed = next((f for f in self.state.failed if f.track_id == track_id), None)
        return failed.attempts if failed else 0

    def set_pending(self, track_ids: List[str]):
        if self.state is None:
            self.load_progress()

        self.state.pending = track_ids
        self.save_progress()

    def reset(self):
        self.state = ProgressState(
            completed=[],
            failed=[],
            pending=[],
            last_updated=datetime.utcnow().isoformat() + 'Z'
        )
        self.save_progress()
