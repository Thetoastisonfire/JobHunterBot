"""
search/semantic_search.py

O*NET-backed replacement for the TF-IDF/embedding fallback. Public API
is unchanged (search(query, k, threshold) -> list[(title, score)]), so
search_pipeline.py needs no changes.

O*NET ships its own curated occupation relatedness in
related_occupations: for every occupation, up to 20 other occupations
ranked into three tiers (Primary-Short, Primary-Long, Supplemental) by
related_index. This replaces the cosine-similarity step entirely --
no embeddings, no vectorizer, no "offline TF-IDF fallback" warning.

It also directly fixes the query-drift problem the TF-IDF fallback
had (pulling in "Software Architect" / "Principal Engineer" for a
plain "software engineer" query): those show up as Supplemental-tier
relations for "Software Developers" in O*NET's own data, which score
low enough to fall below SEMANTIC_SCORE_THRESHOLD by default.

Score mapping (tier + in-tier rank -> a 0-1 score comparable to the
old cosine-similarity threshold):
    Primary-Short:  0.80 - 1.00  (rank 1 highest)
    Primary-Long:   0.50 - 0.65
    Supplemental:   0.15 - 0.30
These bands are a deliberate design choice, not something O*NET
publishes -- tune them (or SEMANTIC_SCORE_THRESHOLD in config.py) if
results feel too loose/tight for your use case.
"""

from synonym_finder_v2.config import SEMANTIC_SCORE_THRESHOLD, TOP_K
from synonym_finder_v2.ONET_db.onet_repo import code_for_title, related_codes
from synonym_finder_v2.search.synonym_lookup import find_canonical

_TIER_SCORE_RANGE = {
    "Primary-Short": (1.00, 0.80),
    "Primary-Long": (0.65, 0.50),
    "Supplemental": (0.30, 0.15),
}
_TIER_RANK_SPAN = 20  # O*NET lists at most 20 related occupations total


def _score(tier: str, rank: int) -> float:
    high, low = _TIER_SCORE_RANGE.get(tier, (0.0, 0.0))
    # rank is O*NET's overall 1-20 related_index, not per-tier, but
    # using it as a tiebreaker within a tier's range is close enough
    # for ranking purposes and keeps this simple.
    fraction = min(max((rank - 1) / _TIER_RANK_SPAN, 0.0), 1.0)
    return high - (high - low) * fraction


def search(
    query: str,
    k: int = TOP_K,
    threshold: float = SEMANTIC_SCORE_THRESHOLD,
) -> list[tuple[str, float]]:
    """Returns up to `k` (related_canonical_title, score) tuples for the
    occupation that `query` resolves to, filtered by `threshold` and
    ordered by descending score. `query` may already be a canonical
    title (the pipeline's common case) or raw normalized text."""
    code = code_for_title(query)
    if code is None:
        canonical = find_canonical(query)
        if canonical is None:
            return []
        code = code_for_title(canonical)
        if code is None:
            return []

    results: list[tuple[str, float]] = []
    for title, tier, rank in related_codes(code, limit=k):
        score = _score(tier, rank)
        if score >= threshold:
            results.append((title, score))
    return results
