"""
Fetchers for job listings.

- Greenhouse / Lever / Ashby: official public job-board APIs, no auth needed.
  These feed the "auto-apply" lane since we know their form structure.
- Adzuna: legitimate job-search aggregator API (free tier, requires a free
  API key from https://developer.adzuna.com/). Feeds the "notify-only" lane
  since applications from here point to arbitrary external sites.
"""

import os
import requests

TIMEOUT = 15


def fetch_greenhouse_jobs(board_token: str) -> list[dict]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{board_token}/jobs"
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    jobs = r.json().get("jobs", [])
    return [
        {
            "id": f"greenhouse:{board_token}:{j['id']}",
            "title": j["title"],
            "location": (j.get("location") or {}).get("name", ""),
            "url": j["absolute_url"],
            "ats": "greenhouse",
            "board_token": board_token,
            "raw_id": j["id"],
        }
        for j in jobs
    ]


def fetch_lever_jobs(board_token: str) -> list[dict]:
    url = f"https://api.lever.co/v0/postings/{board_token}?mode=json"
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    jobs = r.json()
    return [
        {
            "id": f"lever:{board_token}:{j['id']}",
            "title": j["text"],
            "location": (j.get("categories") or {}).get("location", ""),
            "url": j["hostedUrl"],
            "ats": "lever",
            "board_token": board_token,
            "raw_id": j["id"],
        }
        for j in jobs
    ]


def fetch_ashby_jobs(board_token: str) -> list[dict]:
    url = f"https://api.ashbyhq.com/posting-api/job-board/{board_token}"
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    jobs = r.json().get("jobs", [])
    return [
        {
            "id": f"ashby:{board_token}:{j['id']}",
            "title": j["title"],
            "location": j.get("location", ""),
            "url": j["jobUrl"],
            "ats": "ashby",
            "board_token": board_token,
            "raw_id": j["id"],
        }
        for j in jobs
    ]


def fetch_all_company_jobs(companies: list[dict]) -> list[dict]:
    """Fetch jobs from every company in config.yaml's `companies` list."""
    all_jobs = []
    fetchers = {
        "greenhouse": fetch_greenhouse_jobs,
        "lever": fetch_lever_jobs,
        "ashby": fetch_ashby_jobs,
    }
    for company in companies:
        ats = company["ats"]
        token = company["board_token"]
        fetcher = fetchers.get(ats)
        if not fetcher:
            print(f"[warn] unknown ATS '{ats}' for {company['name']}, skipping")
            continue
        try:
            jobs = fetcher(token)
            for j in jobs:
                j["company_name"] = company["name"]
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"[warn] failed to fetch jobs for {company['name']} ({ats}): {e}")
    return all_jobs


def fetch_adzuna_jobs(keyword: str, country: str, results: int = 20,
                       max_days_old: int = 0, salary_min: int = 0) -> list[dict]:
    """
    Notify-only broad search via Adzuna's public API.
    Requires ADZUNA_APP_ID and ADZUNA_APP_KEY environment variables
    (free signup at https://developer.adzuna.com/).
    """
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        print("[warn] ADZUNA_APP_ID / ADZUNA_APP_KEY not set, skipping broad search")
        return []

    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": results,
        "what": keyword,
        "content-type": "application/json",
    }
    if max_days_old:
        params["max_days_old"] = max_days_old
    if salary_min:
        params["salary_min"] = salary_min

    r = requests.get(url, params=params, timeout=TIMEOUT)
    r.raise_for_status()
    results_json = r.json().get("results", [])
    return [
        {
            "id": f"adzuna:{j['id']}",
            "title": j.get("title", ""),
            "location": (j.get("location") or {}).get("display_name", ""),
            "url": j.get("redirect_url", ""),
            "ats": "adzuna",
            "company_name": (j.get("company") or {}).get("display_name", "Unknown"),
        }
        for j in results_json
    ]
