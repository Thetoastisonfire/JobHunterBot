"""Persistence for the 'seen jobs' de-dupe set, with a 2-week rolling reset."""
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from .config import CACHE_RESET_FILE, SEEN_FILE


def load_seen(seen_file: str = SEEN_FILE) -> set[Any]:
    if Path(seen_file).exists():
        content = Path(seen_file).read_text().strip()
        if content:
            return set(json.loads(content))
    return set()


def save_seen(seen: set[Any], seen_file: str = SEEN_FILE, reset_file: str = CACHE_RESET_FILE) -> None:
    now = datetime.now()
    reset_path = Path(reset_file)

    should_clear = True
    if reset_path.exists():
        try:
            last_reset = datetime.fromisoformat(reset_path.read_text().strip())
            should_clear = now - last_reset >= timedelta(days=14)
        except (ValueError, TypeError):
            pass  # Empty or malformed file -> clear cache and rewrite timestamp

    if should_clear:
        seen.clear()  # Start fresh every 2 weeks
        reset_path.write_text(now.isoformat())

    Path(seen_file).write_text(json.dumps(sorted(seen), indent=2))
