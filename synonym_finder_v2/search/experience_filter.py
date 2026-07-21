"""
search/experience_filter.py

Two independent, complementary signals for filtering by experience
level, neither of which is max_years_in_text() (which stays exactly
as you have it, reading explicit numbers stated in the posting text):

  1. title_has_senior_word(title) -- word-list check, catches titles
     that use an explicit seniority word ("Senior", "Staff",
     "Principal", "Director", ...). This is the direct replacement for
     your old SENIOR_TITLE_RE.

  2. estimate_min_years_for_title(title) -- O*NET Job Zone lookup on
     the *occupation* the title resolves to. This catches a DIFFERENT
     failure mode: postings for a fundamentally more senior occupation
     category that never use a seniority word at all (e.g.
     "Engineering Manager" implies more years than "Software Engineer"
     even with no "senior" in sight).

IMPORTANT LIMITATION (found by testing, not theoretical): Job Zone is
assigned per O*NET OCCUPATION, not per seniority level within an
occupation. "Software Engineer", "Staff Software Engineer", and
"Principal Software Engineer" all resolve to the same O*NET occupation
("Software Developers") and therefore the same Job Zone -- O*NET
doesn't distinguish them, and normalize() strips the very seniority
words that would signal the difference before the O*NET lookup runs.
So estimate_min_years_for_title() CANNOT replace SENIOR_TITLE_RE-style
detection on its own -- that's what (1) is for. Use both.
"""

import json
import os
import re

from synonym_finder_v2.config import DATA_DIR, JOB_ZONE_MIN_YEARS
from synonym_finder_v2.search.normalize import normalize
from synonym_finder_v2.ONET_db.onet_repo import code_for_title, exact_lookup, job_zone_for_code

_SENIOR_WORDS_PATH = os.path.join(DATA_DIR, "senior_title_words.json")
_senior_re: re.Pattern[str] | None = None


def _load_senior_re() -> re.Pattern[str]:
    global _senior_re
    if _senior_re is None:
        with open(_SENIOR_WORDS_PATH, "r", encoding="utf-8") as f:
            words = json.load(f)["words"]
        _senior_re = re.compile(
            r"\b(" + "|".join(re.escape(w) for w in words) + r")\b", re.IGNORECASE
        )
    return _senior_re


def title_has_senior_word(title: str) -> bool:
    """Direct replacement for the old SENIOR_TITLE_RE.search(...) check:
    does the title contain an explicit seniority word? Kept as a
    separate word list from xp_level.json's levels (used by
    normalize() to strip both junior AND senior words for O*NET
    matching) since this check only cares about the senior direction."""
    if not title:
        return False
    return bool(_load_senior_re().search(title))


def estimate_min_years_for_title(raw_title: str) -> int | None:
    """Resolves a raw job-posting title to an O*NET occupation and
    returns the typical minimum years of experience implied by its Job
    Zone (currently only Zone 5 yields a number -- see
    JOB_ZONE_MIN_YEARS in config.py for why). Returns None if the
    title can't be resolved, the occupation has no Job Zone on record,
    or the zone doesn't have a safe numeric signal -- callers should
    treat None as "no signal", not "zero years".

    Deliberately EXACT match only, no fuzzy fallback. find_canonical's
    fuzzy matching was designed for clean, short user search queries;
    real job-posting titles are noisier ("QA Engineer II", "QA
    Automation Engineer - Contract") and in testing this produced a
    wrong-occupation false positive (fuzzy-matched "QA Engineer" to
    "Automotive Engineers"). A silently wrong occupation match here
    would mis-filter real postings, so this only acts when a title
    matches an O*NET title/alternate-title/reported-title exactly."""
    if not raw_title or not raw_title.strip():
        return None

    canonical = exact_lookup(normalize(raw_title))
    if not canonical:
        return None

    code = code_for_title(canonical)
    if not code:
        return None

    zone = job_zone_for_code(code)
    if zone is None:
        return None

    return JOB_ZONE_MIN_YEARS.get(zone)
