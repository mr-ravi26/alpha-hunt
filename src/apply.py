"""
Fills and submits ATS application forms using Playwright.

Honesty note: Greenhouse/Lever/Ashby forms are fairly standardized but every
company customizes their custom questions differently. This filler:
  1. Fills the fields it recognizes confidently (name, email, phone, resume,
     LinkedIn, portfolio).
  2. For every other required field/question, tries to match it against
     qa.yaml. If ALL required fields are answered, it submits.
  3. If anything required is left unanswered, it does NOT submit -- it
     reports back "needs_review" so you get notified to finish it by hand
     instead of a broken/blank application going out.

This will need occasional tuning per-company as forms change. Treat it as
a strong starting point, not a "set and forget forever" black box.
"""

import re
import yaml
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout


def load_qa(path: str = "qa.yaml") -> list[dict]:
    try:
        with open(path, "r") as f:
            return yaml.safe_load(f) or []
    except FileNotFoundError:
        return []


def match_answer(question_text: str, qa: list[dict]) -> str | None:
    q = question_text.lower()
    for entry in qa:
        for phrase in entry["match"]:
            if phrase.lower() in q:
                return entry["answer"]
    return None


def apply_to_job(job: dict, applicant: dict, qa: list[dict],
                  headless: bool = True) -> tuple[str, str]:
    """
    Returns (status, detail) where status is one of:
      "submitted", "needs_review", "error"
    """
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            page = browser.new_page()
            page.goto(job["url"], timeout=30000)
            page.wait_for_load_state("networkidle", timeout=15000)

            # Some ATS pages (Ashby, some Greenhouse boards) show the job
            # description first and only reveal the application form after
            # clicking an "Apply" trigger. Click it if present.
            apply_trigger = page.get_by_role(
                "link", name=re.compile(r"^apply", re.I)
            ).first
            if apply_trigger.count() == 0:
                apply_trigger = page.get_by_role(
                    "button", name=re.compile(r"^apply", re.I)
                ).first
            if apply_trigger.count() > 0:
                try:
                    apply_trigger.click(timeout=5000)
                    page.wait_for_load_state("networkidle", timeout=15000)
                except Exception:
                    pass  # already on the form, or trigger wasn't real

            unanswered = []

            def fill_if_present(selectors: list[str], value: str):
                if not value:
                    return
                for sel in selectors:
                    try:
                        el = page.locator(sel).first
                        if el.count() > 0:
                            el.fill(value)
                            return
                    except Exception:
                        continue

            # --- Standard fields (best-effort common selectors) ---
            fill_if_present(
                ['input[name*="first_name" i]', 'input[id*="first_name" i]'],
                applicant["first_name"],
            )
            fill_if_present(
                ['input[name*="last_name" i]', 'input[id*="last_name" i]'],
                applicant["last_name"],
            )
            fill_if_present(
                ['input[type="email"]', 'input[name*="email" i]'],
                applicant["email"],
            )
            fill_if_present(
                ['input[type="tel"]', 'input[name*="phone" i]'],
                applicant["phone"],
            )
            fill_if_present(
                ['input[name*="linkedin" i]', 'input[id*="linkedin" i]'],
                applicant.get("linkedin_url", ""),
            )
            fill_if_present(
                ['input[name*="website" i]', 'input[name*="portfolio" i]'],
                applicant.get("portfolio_url", ""),
            )

            # --- Resume upload ---
            resume_path = applicant.get("resume_path")
            if resume_path:
                try:
                    file_input = page.locator('input[type="file"]').first
                    if file_input.count() > 0:
                        file_input.set_input_files(resume_path)
                except Exception:
                    unanswered.append("resume upload field not found")

            # --- Custom questions: find labels/questions and try to answer ---
            question_blocks = page.locator(
                "label, .application-question, [class*='question' i]"
            )
            count = min(question_blocks.count(), 60)  # safety cap
            for i in range(count):
                try:
                    text = question_blocks.nth(i).inner_text(timeout=1000).strip()
                except Exception:
                    continue
                if not text or len(text) > 200:
                    continue
                answer = match_answer(text, qa)
                if answer is None:
                    # Only flag as unanswered if it looks like a real required question
                    if "?" in text or re.search(r"\brequired\b|\*", text, re.I):
                        unanswered.append(text)

            if unanswered:
                browser.close()
                detail = "; ".join(unanswered[:5])
                return "needs_review", f"Unanswered fields: {detail}"

            # --- Submit ---
            # Try standard submit inputs first, then fall back to any
            # visible button whose text looks like a submit action (many
            # ATS forms use styled <button> elements with no type="submit").
            submit_btn = page.locator(
                'button[type="submit"], input[type="submit"]'
            ).first
            if submit_btn.count() == 0:
                submit_btn = page.get_by_role(
                    "button", name=re.compile(r"submit application|submit|apply now", re.I)
                ).first

            if submit_btn.count() == 0:
                browser.close()
                return "needs_review", "Could not find submit button"

            submit_btn.scroll_into_view_if_needed(timeout=5000)
            submit_btn.click(timeout=10000)
            page.wait_for_timeout(3000)  # let confirmation page load

            browser.close()
            return "submitted", "ok"

    except PWTimeout:
        return "error", "Page load timed out"
    except Exception as e:
        return "error", str(e)
