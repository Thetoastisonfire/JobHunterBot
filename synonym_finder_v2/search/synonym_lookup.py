"""
search/synonym_lookup.py

O*NET-backed replacement for the old synonym_groups.json lookup.
Public API is unchanged (find_canonical, get_synonyms_for_canonical),
so search_pipeline.py needs no changes.

Exact match now checks three O*NET sources instead of one hand-edited
file:
  - occupation_data.title      (the ~1000 official occupation names)
  - job_titles.job_title/short_title (O*NET's curated alternate titles,
    ~57k rows -- this is the real synonym set)
  - sample_of_reported_titles.reported_job_title (crowd-reported
    titles, ~8k rows -- messier but catches real-world phrasing)

Fuzzy match runs over the union of all three (~65k aliases) using
rapidfuzz instead of difflib, since difflib's SequenceMatcher over
that many strings per query would be too slow to run per-request.
"""

from synonym_finder_v2.ONET_db.onet_repo import exact_lookup, fuzzy_lookup, code_for_title, synonyms_for_code


def get_synonyms_for_canonical(canonical: str) -> list[str]:
    """Returns the alternate/reported titles for a canonical occupation
    title, or [] if the title isn't found."""
    code = code_for_title(canonical)
    if not code:
        return []
    return synonyms_for_code(code)


def find_canonical(normalized_query: str, fuzzy_threshold: float = 0.87) -> str | None:
    """Exact match first (occupation titles + alternate titles +
    reported titles), then a fuzzy match over the same pool. Returns
    the canonical occupation title, or None if nothing matches closely
    enough."""
    exact = exact_lookup(normalized_query)
    if exact:
        return exact
    return fuzzy_lookup(normalized_query, threshold=fuzzy_threshold)
