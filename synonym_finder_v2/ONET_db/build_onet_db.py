"""
scripts/build_onet_db.py

One-time (re-runnable) import of the O*NET database SQL dump into a
local SQLite file used by the search pipeline.

Usage:
    python scripts/build_onet_db.py /path/to/onet_sql_dir

Only the tables the search pipeline actually needs are loaded (see
ONET_MIGRATION.md for why each one is included). The full O*NET
distribution has 45 files covering skills/abilities/tasks/etc that
this project doesn't use yet.
"""

import pathlib
import sqlite3

from synonym_finder_v2.config import SQL_DIR, ONET_DB_PATH

# Loaded in dependency order: occupation_data is referenced by all the
# others via FOREIGN KEY, so it goes first. SQLite doesn't enforce FKs
# by default, but keeping the order sane avoids surprises if that's
# ever turned on.
REQUIRED_FILES = [
    "03_occupation_data",
    "02_job_zone_reference",
    "21_job_zones",
    "36_job_titles",
    "37_sample_of_reported_titles",
    "35_related_occupations",
]


def build(sql_dir: pathlib.Path, db_path: pathlib.Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db_path.unlink(missing_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        for name in REQUIRED_FILES:
            path = sql_dir / f"{name}.sql"
            if not path.exists():
                raise FileNotFoundError(f"Missing expected O*NET file: {path}")
            sql = path.read_text(encoding="utf-8")
            # The dump's /*! ... */ MySQL-style conditional comments
            # parse fine as plain SQL comments under sqlite3.
            conn.executescript(sql)
            print(f"loaded {name}")
        conn.commit()

        # A couple of indexes that matter a lot once this is queried
        # per-request instead of loaded once for a demo script.
        conn.executescript(
            """
            CREATE INDEX IF NOT EXISTS idx_job_titles_code
                ON job_titles(onetsoc_code);
            CREATE INDEX IF NOT EXISTS idx_reported_titles_code
                ON sample_of_reported_titles(onetsoc_code);
            CREATE INDEX IF NOT EXISTS idx_related_code
                ON related_occupations(onetsoc_code, related_index);
            CREATE INDEX IF NOT EXISTS idx_occupation_title_lower
                ON occupation_data(title);
            """
        )
        conn.commit()
    finally:
        conn.close()


def build_db():
    sql_dir = pathlib.Path(SQL_DIR)
    db_path = pathlib.Path(ONET_DB_PATH)
    build(sql_dir, db_path)
    print(f"\nBuilt {db_path}")
