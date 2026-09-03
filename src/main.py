"""
Entry point. Run this on a schedule (every 15-30 min recommended).

    python src/main.py
"""

import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(__file__))

from sources import fetch_all_company_jobs, fetch_adzuna_jobs
from state import (
    load_seen, save_seen, filter_new_jobs,
    get_today_broad_count, increment_today_broad_count,
)
from notify import send_telegram, format_applied, format_needs_review, format_notify_only
from apply import apply_to_job, load_qa


def main():
    with open("config.yaml", "r") as f:
        cfg = yaml.safe_load(f)

    keywords = cfg["keywords"]
    must_include_all = cfg.get("must_include_all", [])
    locations = cfg.get("locations", [])
    exclude_keywords = cfg.get("exclude_keywords", [])
    applicant = cfg["applicant"]
    settings = cfg.get("settings", {})
    max_apps = settings.get("max_applications_per_run", 15)
    max_broad_per_run = settings.get("max_broad_notifications_per_run", 8)
    max_broad_per_day = settings.get("max_broad_notifications_per_day", 25)

    seen = load_seen()
    qa = load_qa("qa.yaml")

    applied_count = 0

    # ---------- Lane 1: company ATS boards (auto-apply) ----------
    print("Fetching jobs from tracked companies...")
    company_jobs = fetch_all_company_jobs(cfg.get("companies", []))
    new_company_jobs = filter_new_jobs(
        company_jobs, seen, keywords, locations, exclude_keywords, must_include_all
    )
    print(f"Found {len(new_company_jobs)} new matching jobs from tracked companies.")

    for job in new_company_jobs:
        if applied_count >= max_apps:
            print("Hit max_applications_per_run limit, stopping auto-apply for this run.")
            break

        status, detail = apply_to_job(job, applicant, qa)
        seen.add(job["id"])  # mark seen either way so we don't retry endlessly

        if status == "submitted":
            applied_count += 1
            send_telegram(format_applied(job))
            print(f"[submitted] {job['company_name']} - {job['title']}")
        elif status == "needs_review":
            send_telegram(format_needs_review(job, detail))
            print(f"[needs review] {job['company_name']} - {job['title']}: {detail}")
        else:
            send_telegram(format_needs_review(job, f"Error: {detail}"))
            print(f"[error] {job['company_name']} - {job['title']}: {detail}")

    # ---------- Lane 2: broad keyword search (notify-only, capped) ----------
    broad_cfg = cfg.get("broad_search", {})
    if broad_cfg.get("enabled"):
        already_today = get_today_broad_count()
        remaining_today = max(0, max_broad_per_day - already_today)
        run_budget = min(max_broad_per_run, remaining_today)

        if run_budget <= 0:
            print(f"Daily broad-notification cap ({max_broad_per_day}) reached, skipping broad search.")
        else:
            print("Running broad keyword search...")
            broad_jobs = []
            for kw in keywords:
                broad_jobs.extend(
                    fetch_adzuna_jobs(
                        kw,
                        broad_cfg.get("adzuna_country", "in"),
                        broad_cfg.get("results_per_search", 20),
                        broad_cfg.get("max_days_old", 0),
                        broad_cfg.get("salary_min", 0),
                    )
                )
            new_broad_jobs = filter_new_jobs(
                broad_jobs, seen, keywords, locations, exclude_keywords, must_include_all
            )
            # Cap to the remaining budget for this run/day
            to_send = new_broad_jobs[:run_budget]
            skipped = len(new_broad_jobs) - len(to_send)
            print(f"Found {len(new_broad_jobs)} new matches, sending {len(to_send)} "
                  f"(capped, {skipped} held back).")

            for job in to_send:
                seen.add(job["id"])
                send_telegram(format_notify_only(job))

            # Mark the rest as seen too, so we don't re-evaluate them forever,
            # but they simply won't be notified about this run.
            for job in new_broad_jobs[len(to_send):]:
                seen.add(job["id"])

            increment_today_broad_count(len(to_send))

    save_seen(seen)
    print(f"Run complete. {applied_count} applications submitted this run.")


if __name__ == "__main__":
    main()
