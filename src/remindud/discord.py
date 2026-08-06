"""Discord webhook client."""

from __future__ import annotations

import os

import httpx

from remindud.models import Reminder


class DiscordError(RuntimeError):
    pass


def webhook_url_from_env() -> str:
    url = os.environ.get("DISCORD_WEBHOOK_URL", "").strip()
    if not url:
        raise DiscordError(
            "DISCORD_WEBHOOK_URL is not set. Add it as a GitHub secret or export it locally."
        )
    return url


def build_payload(reminder: Reminder) -> dict:
    return {
        "content": reminder.message,
        "embeds": [
            {
                "title": reminder.title,
                "description": reminder.message,
                "color": 0x5865F2,
                "footer": {"text": f"remindud · {reminder.schedule_summary()}"},
            }
        ],
        "allowed_mentions": {"parse": ["users", "roles"]},
    }


def send_reminder(
    reminder: Reminder,
    *,
    webhook_url: str | None = None,
    dry_run: bool = False,
) -> None:
    url = webhook_url or webhook_url_from_env()
    payload = build_payload(reminder)

    if dry_run:
        print(f"[dry-run] would send: {reminder.title!r} → {reminder.message!r}")
        return

    with httpx.Client(timeout=30.0) as client:
        response = client.post(url, json=payload)
        if response.status_code >= 400:
            raise DiscordError(
                f"Discord webhook failed ({response.status_code}): {response.text}"
            )
