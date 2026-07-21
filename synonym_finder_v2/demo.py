"""
demo.py

Quick manual test of the pipeline.

    python demo.py "software engineer"
    python demo.py "sr swe"
    python demo.py "growth marketer"

If no argument is given, defaults to "software engineer".
"""

import sys

from synonym_finder_v2.search.search_pipeline import get_synonyms

def main():
   
    query = " ".join(sys.argv[1:]) or "junior software engineer"
    synonyms = get_synonyms(query, n=20)

    print(f"\nQuery: {query!r}")
    print(f"Found {len(synonyms)} related job titles:\n")
    for i, s in enumerate(synonyms, start=1):
        print(f"{i:>2}. {s}")
    print()


if __name__ == "__main__":
    main()
