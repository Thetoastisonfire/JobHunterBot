"""Loads config.json and required environment variables (secrets)."""
import json
import os


def _clean_env(name: str) -> str:
    """Read an env var and strip stray non-breaking spaces / whitespace
    (GitHub Actions secrets sometimes carry a trailing \\xa0)."""
    return os.environ[name].replace("\xa0", "").strip()


def load_config(path: str = "config.json") -> dict[str, str]:
    with open(path) as f:
        return json.load(f)


class Secrets:
    """Loaded once at import time, matching the original script's behavior."""

    def __init__(self):
        self.EMAIL_FROM = _clean_env("EMAIL_FROM")
        self.EMAIL_PASSWORD = _clean_env("EMAIL_PASSWORD")
        self.EMAIL_TO = _clean_env("EMAIL_TO")
        self.ADZUNA_APP_ID = _clean_env("ADZUNA_APP_ID")
        self.ADZUNA_APP_KEY = _clean_env("ADZUNA_APP_KEY")


CACHE_RESET_FILE = "last_cache_reset.txt"
CACHE_RESET_TIMEFRAME = 14 * 24 * 60 * 60  # 2 weeks, in seconds
SEEN_FILE = "seen_jobs.json"
MAX_SYNONYM = 10  # synonyms pulled from the vector search pipeline per keyword
