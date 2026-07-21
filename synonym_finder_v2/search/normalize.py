"""
search/normalize.py

Cleans up raw user input before it's handed to the rest of the
pipeline: lowercasing, punctuation stripping, whitespace collapsing,
and abbreviation expansion (e.g. "Sr SWE" -> "senior software
engineer").
"""

import json
import re

from synonym_finder_v2.config import ABBREVIATIONS_PATH, LEVEL_RE_FILE_PATH


_PUNCT_RE = re.compile(r"[^\w\s&/-]")
_WHITESPACE_RE = re.compile(r"\s+")


_level_RE: re.Pattern[str] | None = None # contains expressions of work experience levels
_abbreviations_cache: dict[str, str] | None = None # contains abbreviations


def _load_abbreviations():
    global _abbreviations_cache
    if _abbreviations_cache is None:
        with open(ABBREVIATIONS_PATH, "r", encoding="utf-8") as f:
            _abbreviations_cache = json.load(f)
    return _abbreviations_cache

def _load_level_regex():
    global _level_RE
    with open(LEVEL_RE_FILE_PATH, "r", encoding="utf-8") as f:
        levels = json.load(f)["levels"]

    _level_RE = re.compile(
        r"\b(" + "|".join(re.escape(level) for level in levels) + r")\b",
        re.IGNORECASE
    )



def expand_abbreviations(text: str) -> str:
    abbreviations = _load_abbreviations()
    assert abbreviations is not None
    tokens = text.split()
    expanded = [abbreviations.get(tok, tok) for tok in tokens]
    return " ".join(expanded)


def normalize(text: str) -> str:
    global _level_RE
    if _level_RE is None: _load_level_regex() # if not loaded, load experience level expressions
    assert _level_RE is not None

    """Lowercase, strip punctuation, collapse whitespace, expand known
    abbreviations. Returns a clean string ready for synonym lookup or
    embedding."""
    text = text.lower().strip()
    text = _PUNCT_RE.sub(" ", text)
    text = _WHITESPACE_RE.sub(" ", text).strip()
    text = expand_abbreviations(text)
    text = _level_RE.sub(" ", text)          # <-- strip level words
    text = _WHITESPACE_RE.sub(" ", text).strip()
    return text
