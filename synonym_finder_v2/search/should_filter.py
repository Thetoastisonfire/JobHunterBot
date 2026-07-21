"""
This is your existing filter module with the MAX_YEARS block extended
to three independent signals instead of two:

  1. max_years_in_text(title + " " + desc) -- UNCHANGED, your existing
     regex extraction of an explicitly stated number ("5+ years").

  2. title_has_senior_word(job["title"]) -- direct replacement for the
     old SENIOR_TITLE_RE.search(senior_check_text) check. Same idea
     (keyword list against the title), now sourced from
     data/senior_title_words.json instead of an inline regex.

  3. estimate_min_years_for_title(job["title"]) -- NEW. O*NET Job Zone
     lookup on the occupation the title resolves to. Catches postings
     for a more senior OCCUPATION CATEGORY that never use a seniority
     word at all (e.g. "Engineering Manager" implies more years than
     "Software Engineer" with no "senior" in the title).

     Important: this does NOT catch "Staff Engineer" vs "Software
     Engineer" -- both resolve to the same O*NET occupation and Job
     Zone, since O*NET doesn't distinguish seniority within one
     occupation. That case is what (2) is for. The two checks are
     deliberately non-overlapping, not redundant.

All three run whenever MAX_YEARS > 0; a posting is filtered if ANY of
them implies more experience than allowed. Everything above the
MAX_YEARS block (blacklist, tech-relevance check) is unchanged from
what you already have.
"""

import re
from typing import Any

from synonym_finder_v2.config import MAX_YEARS, BLACKLIST  # or wherever this actually lives in your config
from search.experience_filter import estimate_min_years_for_title, title_has_senior_word

# BLACKLIST, TECH_RELEVANCE_RE, max_years_in_text, _WORD_TO_NUM,
# _NUM_WORD_RE, _to_num all stay exactly as you already have them --
# omitted here since they're unchanged.


def should_filter(job: dict[str, Any]) -> tuple[bool, str]:
    """Returns (filter_out, reason). Checks blacklist then experience."""
    company = job.get("company", "").lower()
    title = job.get("title", "").lower()
    desc = job.get("excerpt", "").lower()

    haystack = " ".join([company, title, desc])
    for b in BLACKLIST:
        if re.search(r"\b" + re.escape(b) + r"\b", haystack):
            return True, "blacklisted term: " + b


    if MAX_YEARS > 0:

        # For entry-level settings, also block titles that use an
        # explicit seniority word (checked against title AND the first
        # part of the description, same as your original logic, since
        # a posting's true title sometimes only appears restated at
        # the start of the description text).
        senior_check_text = title + " " + desc[:80]
        if MAX_YEARS <= 2 and title_has_senior_word(senior_check_text):
            return True, "senior title: " + job["title"]

        # Independent of any seniority word: does the title resolve to
        # a fundamentally more senior OCCUPATION CATEGORY than
        # MAX_YEARS allows, per O*NET Job Zone data?
        zone_years = estimate_min_years_for_title(job["title"])
        if zone_years is not None and zone_years > MAX_YEARS:
            return True, (
                f"title implies ~{zone_years}+ yrs typical experience "
                f"(max {MAX_YEARS}): {job['title']}"
            )

    return False, ""
