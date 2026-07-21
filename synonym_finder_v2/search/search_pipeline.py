"""
search/search_pipeline.py

Main orchestrator - the only module most of the application needs to
call.

    from search.search_pipeline import get_synonyms
    get_synonyms("software engineer")  # -> list[str], 20 related titles

Pipeline:
    normalize -> synonym lookup -> (found: collect direct synonyms)
              -> semantic search over related canonical jobs to round
                 the list out to the requested count
              -> dedupe / rank -> return
"""

from typing import Any
from synonym_finder_v2.config import SYNONYM_RESULT_COUNT, SEMANTIC_SCORE_THRESHOLD
from synonym_finder_v2.search.normalize import normalize
from synonym_finder_v2.search.semantic_search import search as semantic_search
from synonym_finder_v2.search.synonym_lookup import find_canonical, get_synonyms_for_canonical


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key: str = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


def get_synonyms(query: str, n: int = SYNONYM_RESULT_COUNT) -> list[str]:
    """Returns up to `n` job-title strings related to `query`.

    1. Normalize the input (lowercase, expand abbreviations, etc).
    2. Try an exact/fuzzy synonym-group lookup.
    3. If that resolves to a canonical title, collect its direct
       synonyms (plus the canonical title itself), then run semantic
       search over the canonical-job embeddings to find the closest
       *other* job titles, and borrow their synonyms to round the list
       out to `n`.
    4. If no synonym-group match exists at all, skip straight to
       semantic search and build the list purely from the closest
       matching canonical jobs' synonym groups.
    """
    if not query or not query.strip():
        return []

    normalized = normalize(query)
    canonical = find_canonical(normalized)

    results: list[str] = []
    ordered_canonicals: list[str] = []

    if canonical:
        ordered_canonicals.append(canonical)
        results.append(canonical)
        results.extend(get_synonyms_for_canonical(canonical))

    # Always run semantic search, both to fill any remaining slots and
    # to cover the "no direct synonym-group match at all" case.
    semantic_matches: list[tuple[Any, float]] = semantic_search(canonical if canonical else normalized)
    for matched_canonical, score in semantic_matches: # for each semantic match, check if they're a fit
        if score < SEMANTIC_SCORE_THRESHOLD:
            continue
        if matched_canonical not in ordered_canonicals:
            ordered_canonicals.append(matched_canonical)


    for matched_canonical in ordered_canonicals:
        if len(_dedupe_preserve_order(results)) >= n:
            break
        if matched_canonical != canonical:
            results.append(matched_canonical)
        results.extend(get_synonyms_for_canonical(matched_canonical))

    results = _dedupe_preserve_order(results)

    # Never surface the user's own query text as one of its "synonyms"
    results = [r for r in results if r.lower() != query.strip().lower()]

    return results[:n]
