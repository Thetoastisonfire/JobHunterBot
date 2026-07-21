"""
search/onet_repo.py

Thin data-access layer over the O*NET SQLite DB (built by
scripts/build_onet_db.py). synonym_lookup.py and semantic_search.py
both sit on top of this rather than talking to sqlite directly, so
there's one place that knows the schema.

Terminology used throughout this module:
- "canonical" = an occupation_data.title string, e.g. "Software
  Developers". This is what the rest of the pipeline (search_pipeline.py,
  demo.py) treats as the display/grouping key -- same role the old
  hand-written canonical_jobs.json played.
- "code" = the O*NET-SOC code (e.g. "15-1252.00"), the actual primary
  key. Titles aren't unique-safe to key off internally (O*NET titles
  are unique in this dataset, but relying on that long-term is
  fragile), so lookups resolve title -> code -> related data.
"""

from __future__ import annotations

import sqlite3
from functools import lru_cache

from rapidfuzz import fuzz, process

from synonym_finder_v2.config import ONET_DB_PATH

_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(ONET_DB_PATH, check_same_thread=False)
        _conn.row_factory = sqlite3.Row
    return _conn


def title_for_code(code: str) -> str | None:
    row = _get_conn().execute(
        "SELECT title FROM occupation_data WHERE onetsoc_code = ?", (code,)
    ).fetchone()
    return row["title"] if row else None


def code_for_title(title: str) -> str | None:
    row = _get_conn().execute(
        "SELECT onetsoc_code FROM occupation_data WHERE lower(title) = lower(?)",
        (title,),
    ).fetchone()
    return row["onetsoc_code"] if row else None


def exact_lookup(normalized_query: str) -> str | None:
    """Exact (case-insensitive) match against occupation titles, O*NET's
    curated alternate titles, and crowd-reported titles. Returns the
    canonical occupation title, or None."""
    q = normalized_query.strip().lower()
    if not q:
        return None

    row = _get_conn().execute(
        """
        SELECT o.title AS title FROM occupation_data o WHERE lower(o.title) = ?
        UNION
        SELECT o.title AS title
        FROM job_titles j JOIN occupation_data o USING (onetsoc_code)
        WHERE lower(j.job_title) = ? OR lower(j.short_title) = ?
        UNION
        SELECT o.title AS title
        FROM sample_of_reported_titles s JOIN occupation_data o USING (onetsoc_code)
        WHERE lower(s.reported_job_title) = ?
        LIMIT 1
        """,
        (q, q, q, q),
    ).fetchone()
    return row["title"] if row else None


@lru_cache(maxsize=1)
def _alias_index() -> dict[str, str]:
    """lowercased alias string -> onetsoc_code, built once from every
    title source. ~65k entries; rapidfuzz handles that in well under a
    second per query (see fuzzy_lookup)."""
    conn = _get_conn()
    index: dict[str, str] = {}

    for row in conn.execute("SELECT onetsoc_code, title FROM occupation_data"):
        index[row["title"].lower()] = row["onetsoc_code"]

    for row in conn.execute("SELECT onetsoc_code, job_title, short_title FROM job_titles"):
        index.setdefault(row["job_title"].lower(), row["onetsoc_code"])
        if row["short_title"]:
            index.setdefault(row["short_title"].lower(), row["onetsoc_code"])

    for row in conn.execute(
        "SELECT onetsoc_code, reported_job_title FROM sample_of_reported_titles"
    ):
        index.setdefault(row["reported_job_title"].lower(), row["onetsoc_code"])

    return index


def fuzzy_lookup(normalized_query: str, threshold: float = 0.87) -> str | None:
    """Fuzzy match against the full alias index (catches typos like
    'sofware engineer'). threshold is a 0-1 ratio, consistent with the
    old difflib-based fuzzy_threshold."""
    q = normalized_query.strip().lower()
    if not q:
        return None

    aliases = _alias_index()
    match = process.extractOne(
        q, aliases.keys(), scorer=fuzz.ratio, score_cutoff=threshold * 100
    )
    if not match:
        return None

    alias_matched = match[0]
    code = aliases[alias_matched]
    return title_for_code(code)


def synonyms_for_code(code: str) -> list[str]:
    """All known alternate/reported titles for an occupation, excluding
    the canonical title itself, ordered roughly by relevance rather
    than alphabetically.

    Some occupations (e.g. "Software Developers") have 90+ alternate
    titles, easily enough to fill an entire result list on their own,
    so ordering here directly determines what the caller sees at the
    top. Two relevance signals O*NET actually gives us:
      - job_titles.sources: a comma-separated list of which O*NET data
        sources reported this title. More sources = more independently
        corroborated = a more "standard" title.
      - sample_of_reported_titles.shown_in_my_next_move: O*NET's own
        flag for which reported titles it surfaces on its public
        consumer-facing site (a reasonable proxy for "commonly
        recognized"), so those are prioritized over the long tail of
        raw reported titles.
    """
    conn = _get_conn()

    job_title_rows = conn.execute(
        """
        SELECT job_title AS t,
               (length(sources) - length(replace(sources, ',', '')) + 1) AS source_count
        FROM job_titles
        WHERE onetsoc_code = ?
        ORDER BY source_count DESC, job_title ASC
        """,
        (code,),
    ).fetchall()

    reported_rows = conn.execute(
        """
        SELECT reported_job_title AS t
        FROM sample_of_reported_titles
        WHERE onetsoc_code = ?
        ORDER BY shown_in_my_next_move DESC, reported_job_title ASC
        """,
        (code,),
    ).fetchall()

    seen: set[str] = set()
    out: list[str] = []
    for row in list(job_title_rows) + list(reported_rows):
        title = row["t"]
        if title.lower() not in seen:
            seen.add(title.lower())
            out.append(title)
    return out


def job_zone_reference_text(zone: int) -> dict[str, str] | None:
    """Returns the O*NET Job Zone reference row (name/experience/
    education/job_training/examples/svp_range) for a given zone number,
    or None. Useful for surfacing *why* a filter decision was made
    (e.g. in a debug log or admin UI) rather than just a bare number."""
    row = _get_conn().execute(
        "SELECT * FROM job_zone_reference WHERE job_zone = ?", (zone,)
    ).fetchone()
    return dict(row) if row else None


def job_zone_for_code(code: str) -> int | None:
    """Returns the O*NET Job Zone (1-5) for an occupation code, or None
    if that occupation has no Job Zone on record (a handful of broad
    "umbrella" occupations don't)."""
    row = _get_conn().execute(
        "SELECT job_zone FROM job_zones WHERE onetsoc_code = ?", (code,)
    ).fetchone()
    return int(row["job_zone"]) if row else None


def related_codes(code: str, limit: int) -> list[tuple[str, str, int]]:
    """Returns up to `limit` (related_title, relatedness_tier, rank)
    tuples for a given occupation code, ordered by O*NET's own
    relatedness ranking (related_index, ascending = most related
    first)."""
    rows = _get_conn().execute(
        """
        SELECT o.title AS title, r.relatedness_tier AS tier, r.related_index AS rank
        FROM related_occupations r
        JOIN occupation_data o ON o.onetsoc_code = r.related_onetsoc_code
        WHERE r.onetsoc_code = ?
        ORDER BY r.related_index
        LIMIT ?
        """,
        (code, limit),
    ).fetchall()
    return [(row["title"], row["tier"], row["rank"]) for row in rows]
