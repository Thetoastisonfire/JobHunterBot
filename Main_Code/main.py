"""Entry point: fetch, filter, and email new job listings. Run twice daily via cron."""
from typing import Any

from . import config as cfg
from .adzuna import fetch_jobs
from .cache import load_seen, save_seen
from .filters import should_filter
from .keywords import expand_keyword
from .notifier import send_email


def run() -> None:
    config: dict[str, str] = cfg.load_config()
    secrets = cfg.Secrets()

    blacklist = [b.lower().strip() for b in config.get("blacklist", [])]
    max_years = int(config.get("max_years_experience", 2))  # 0 = no filter
    location = config.get("location", "United States")

    seen: set[Any] = load_seen()
    new_jobs: list[dict[str, Any]] = []
    skipped = 0

    print("Config: max_years=" + str(max_years) + ", blacklist=" + str(blacklist))

    total_queries = 0
    variant_set: set[str] = set()
    for keyword in config["keywords"]:
        variants = expand_keyword(keyword, variant_set)
        print("'" + keyword + "' expands to " + str(len(variants)) + " search variants")
        for variant in variants:
            total_queries += 1
            jobs = fetch_jobs(variant, secrets.ADZUNA_APP_ID, secrets.ADZUNA_APP_KEY,
                               location, label=keyword)
            print("  '" + variant + "' -> " + str(len(jobs)) + " results")
            for job in jobs:
                if job["id"] in seen:
                    continue
                filtered, reason = should_filter(job, blacklist, max_years)
                if filtered:
                    print("    [skip] " + job["title"] + " | " + reason)
                    skipped += 1
                    seen.add(job["id"])  # mark seen so it is not re-checked
                else:
                    new_jobs.append(job)
                    seen.add(job["id"])

    print("\n" + str(total_queries) + " total Adzuna queries run")
    print(str(len(new_jobs)) + " new jobs, " + str(skipped) + " filtered out")

    if new_jobs:
        send_email(new_jobs, secrets.EMAIL_FROM, secrets.EMAIL_PASSWORD, secrets.EMAIL_TO)
    else:
        print("No new jobs - no email sent")

    save_seen(seen)


if __name__ == "__main__":
    run()
