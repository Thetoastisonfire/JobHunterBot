"""
config.py

Central configuration for the whole project. Avoids hardcoding
constants/paths throughout the codebase.
"""

import os
import json

# has to go back one step in the dir path cause config.json isn't in this module
JHB_CONFIG_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "config.json"
)
with open("config.json") as f:
    config = json.load(f)
BLACKLIST: list[str] = [b.lower().strip() for b in config.get("blacklist", [])]
MAX_YEARS = int(config.get("max_years_experience", 0))   # 0 = no filter; 0 by default

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ONET_DIR = os.path.join(BASE_DIR, "ONET_db")


# --- O*NET-backed lookups (replaces canonical_jobs.json, ---
SQL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "relevant_ONET"
)
ONET_DB_PATH = os.path.join(ONET_DIR, "onet.db")


# normalize.py inputs -- unchanged, these still live as hand-edited
# JSON since they're small, project-specific, and not part of O*NET.
ABBREVIATIONS_PATH: str = os.path.join(DATA_DIR, "abbreviations.json")
LEVEL_RE_FILE_PATH: str = os.path.join(DATA_DIR, "xp_level.json")

TOP_K: int = 10  # how many related occupations semantic search considers

SEMANTIC_SCORE_THRESHOLD: float = 0.5
# Min score to accept a related-occupation match. With O*NET's
# tiered relatedness (see search/semantic_search.py), 0.5 admits
# Primary-Short and the top half of Primary-Long, and excludes
# Supplemental-tier relations -- this is what keeps loosely-related
# titles like "Software Architect" out of a "Software Engineer" query.
# Lower it if results feel too sparse; raise it (toward ~0.65-0.8) to
# stay strictly within Primary-Short.

SYNONYM_RESULT_COUNT: int = 20  # default number of synonyms returned per query

# --- Job Zone -> typical minimum years of experience ---
# Sourced from job_zone_reference.experience (loaded into the DB --
# see search/onet_repo.job_zone_reference_text() to read it directly),
# which is THIS project's exact O*NET version's text, not a generic
# paraphrase. Quoting the relevant fragment per zone:
#
#   Zone 2 (covers 1-2 in this version): "little or no previous
#     experience; others require several months to a year of
#     experience" -- no reliable floor, ranges include zero.
#   Zone 3: "three or four years of apprenticeship or several years of
#     vocational training" -- describes TRAINING/preparation duration,
#     not a prior-experience requirement for a job posting; treating
#     it as an experience floor would conflate "time to become
#     qualified" with "years required before you're hired".
#   Zone 4: "accountant must complete four years of college AND work
#     for several years in accounting to be considered qualified" --
#     the one number given ("four years") refers to the COLLEGE DEGREE
#     duration, not experience; "several years" of actual experience
#     is mentioned but never quantified. No safe number to extract.
#   Zone 5: "Many require MORE THAN FIVE YEARS of experience" -- the
#     only zone with an explicit, unambiguous experience-years figure
#     in the source text.
#
# Only Zone 5 is treated as a hard filter signal for exactly that
# reason -- it's the only zone where the source text gives an
# unambiguous experience-years number rather than an education
# duration, a training duration, or an unquantified "several years".
JOB_ZONE_MIN_YEARS: dict[int, int | None] = {
    1: None,
    2: None,
    3: None,
    4: None,
    5: 6,  # "more than five years" -> 6 as the literal floor above 5
}
