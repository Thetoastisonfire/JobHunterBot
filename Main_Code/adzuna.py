"""Fetches job listings from the Adzuna API."""
import json
import re
import time
import urllib.parse
import urllib.request
from typing import Any


def fetch_jobs(keyword: str, app_id: str, app_key: str, location: str,
                label: str | None = None) -> list[dict[str, Any]]:
    label = label or keyword
    params = urllib.parse.urlencode({
        "app_id":           app_id,
        "app_key":          app_key,
        "results_per_page": 50,
        # what_phrase requires the exact phrase to appear (title/description),
        # unlike "what" which loosely OR-matches individual words. This matters
        # a lot here because sort_by=date disables relevance scoring, so with
        # "what" a query like "entry level developer" can surface anything
        # matching just "entry" or "level" (e.g. a Firefighter Recruit posting).
        "what_phrase":      keyword,
        "where":            location,
        "sort_by":          "date",
        "max_days_old":     3,
    })
    url = "https://api.adzuna.com/v1/api/jobs/us/search/1?" + params

    req = urllib.request.Request(url, headers={"Content-Type": "application/json"})
    last_err: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data: dict[str, Any] = json.loads(resp.read())
            break
        except Exception as e:
            last_err = e
            if attempt < 2:
                time.sleep(2 * (attempt + 1))  # brief backoff, then retry
    else:
        print("  !!!  Adzuna request failed for '" + keyword + "' after retries: " + str(last_err))
        return []

    jobs: list[dict[str, Any]] = []
    for item in data.get("results", []):
        redirect_url = item.get("redirect_url", "")
        raw_id = item.get("id")
        if raw_id:
            job_id = str(raw_id)
        else:
            # Fall back to the stable numeric ad id embedded in the URL path
            # (e.g. ".../land/ad/5787050712?se=...&v=..." -> "5787050712")
            # rather than the full URL, whose query-string tracking tokens
            # (se=, v=) change on every request and would otherwise make the
            # same job look "new" on every run.
            m = re.search(r'/ad/(\d+)', redirect_url) or re.search(r'/details/(\d+)', redirect_url)
            job_id = m.group(1) if m else redirect_url.split("?", 1)[0]

        jobs.append({
            "id":       job_id,
            "title":    item.get("title", "Untitled"),
            "company":  item.get("company", {}).get("display_name", ""),
            "location": item.get("location", {}).get("display_name", ""),
            "link":     item.get("redirect_url", ""),
            "excerpt":  item.get("description", "")[:220].strip(),
            "date":     item.get("created", ""),
            "keyword":  label,
        })
    return jobs
