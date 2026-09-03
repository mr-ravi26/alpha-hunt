"""
Filtering logic + persistence of which jobs we've already seen/applied to,
so we never double-apply and only act on genuinely new postings. Also
tracks daily notification counts to cap Telegram noise.
"""

import json
import os
from datetime import date

STATE_FILE = "data/seen_jobs.json"
DAILY_COUNT_FILE = "data/daily_counts.json"


def load_seen() -> set[str]:
    if not os.path.exists(STATE_FILE):
        return set()
    with open(STATE_FILE, "r") as f:
        return set(json.load(f))


def save_seen(seen: set[str]) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(sorted(seen), f, indent=2)


def get_today_broad_count() -> int:
    """Returns how many broad-search notifications have gone out today."""
    if not os.path.exists(DAILY_COUNT_FILE):
        return 0
    with open(DAILY_COUNT_FILE, "r") as f:
        data = json.load(f)
    return data.get(str(date.today()), 0)


def increment_today_broad_count(n: int) -> None:
    os.makedirs(os.path.dirname(DAILY_COUNT_FILE), exist_ok=True)
    data = {}
    if os.path.exists(DAILY_COUNT_FILE):
        with open(DAILY_COUNT_FILE, "r") as f:
            data = json.load(f)
    today = str(date.today())
    data[today] = data.get(today, 0) + n
    # keep only the last 14 days to avoid the file growing forever
    data = dict(sorted(data.items())[-14:])
    with open(DAILY_COUNT_FILE, "w") as f:
        json.dump(data, f, indent=2)


def matches_filters(job: dict, keywords: list[str], locations: list[str],
                     exclude_keywords: list[str], must_include_all: list[str] = None) -> bool:
    title = job.get("title", "").lower()

    if any(ex.lower() in title for ex in exclude_keywords):
        return False

    if keywords and not any(kw.lower() in title for kw in keywords):
        return False

    if must_include_all:
        if not all(req.lower() in title for req in must_include_all):
            return False

    if locations:
        loc = job.get("location", "").lower()
        if not any(l.lower() in loc for l in locations):
            return False

    return True


def filter_new_jobs(jobs: list[dict], seen: set[str], keywords: list[str],
                     locations: list[str], exclude_keywords: list[str],
                     must_include_all: list[str] = None) -> list[dict]:
    fresh = []
    for job in jobs:
        if job["id"] in seen:
            continue
        if not matches_filters(job, keywords, locations, exclude_keywords, must_include_all):
            continue
        fresh.append(job)
    return fresh
