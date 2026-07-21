"""Expands one natural-language keyword into synonym-variant search terms."""
from synonym_finder_v2.search.search_pipeline import get_synonyms

from .config import MAX_SYNONYM


def expand_keyword(keyword: str, variant_set: set[str]) -> list[str]:
    """Expand one keyword into every synonym-combination variant.

    `variant_set` is shared across calls so the same variant is never
    searched twice across different input keywords.
    """
    synonyms: list[str] = [s.lower() for s in get_synonyms(keyword, n=MAX_SYNONYM)]

    for synonym in synonyms:  # for each synonym
        if synonym in variant_set:  # if it's been used before
            synonyms.remove(synonym)  # remove it
        else:
            variant_set.add(synonym)  # otherwise mark it as seen
    return synonyms
