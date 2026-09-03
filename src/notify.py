"""
Telegram notifications.

Setup:
1. Message @BotFather on Telegram, run /newbot, get a bot token.
2. Message your new bot once (anything), then visit
   https://api.telegram.org/bot<TOKEN>/getUpdates
   to find your chat_id in the response.
3. Set env vars TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.
"""

import os
import requests

TIMEOUT = 15


def send_telegram(message: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[warn] TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set, printing instead:")
        print(message)
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        requests.post(
            url,
            data={"chat_id": chat_id, "text": message, "parse_mode": "HTML",
                  "disable_web_page_preview": True},
            timeout=TIMEOUT,
        )
    except Exception as e:
        print(f"[warn] failed to send telegram message: {e}")


def format_applied(job: dict) -> str:
    return (
        f"✅ <b>Application submitted</b>\n"
        f"{job['company_name']} — {job['title']}\n"
        f"{job.get('location', '')}\n"
        f"{job['url']}"
    )


def format_needs_review(job: dict, reason: str) -> str:
    return (
        f"⚠️ <b>Needs your review</b>\n"
        f"{job['company_name']} — {job['title']}\n"
        f"{job.get('location', '')}\n"
        f"Reason: {reason}\n"
        f"{job['url']}"
    )


def format_notify_only(job: dict) -> str:
    return (
        f"🔎 <b>New matching job (apply manually)</b>\n"
        f"{job['company_name']} — {job['title']}\n"
        f"{job.get('location', '')}\n"
        f"{job['url']}"
    )
