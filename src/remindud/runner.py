"""Background runner — evaluate due reminders and send Discord messages."""

from __future__ import annotations

import argparse
import sys
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from remindud.discord import DiscordError, send_reminder
from remindud.models import Reminder, SentState
from remindud.schedule import is_due_on, local_now, local_today, past_preferred_time
from remindud.store import (
    REMINDERS_PATH,
    STATE_PATH,
    load_reminders,
    load_state,
    save_state,
)


def already_sent(state: SentState, reminder: Reminder, on: date) -> bool:
    last = state.last_sent.get(reminder.id)
    return last == on


def mark_sent(state: SentState, reminder: Reminder, on: date) -> None:
    state.last_sent[reminder.id] = on


def due_reminders(
    reminders: list[Reminder],
    state: SentState,
    *,
    now: datetime | None = None,
    ignore_preferred_time: bool = False,
) -> list[tuple[Reminder, date]]:
    due: list[tuple[Reminder, date]] = []
    for reminder in reminders:
        if not reminder.enabled:
            continue
        today = (
            local_today(reminder.timezone)
            if now is None
            else now.astimezone(ZoneInfo(reminder.timezone)).date()
        )
        if not is_due_on(reminder, today):
            continue
        if already_sent(state, reminder, today):
            continue
        if not ignore_preferred_time and not past_preferred_time(reminder, now):
            continue
        due.append((reminder, today))
    return due


def run(
    *,
    reminders_path: Path = REMINDERS_PATH,
    state_path: Path = STATE_PATH,
    dry_run: bool = False,
    ignore_preferred_time: bool = False,
    force_id: str | None = None,
) -> int:
    reminders = load_reminders(reminders_path)
    state = load_state(state_path)
    sent_count = 0
    errors = 0

    if force_id:
        targets = [r for r in reminders if r.id == force_id]
        if not targets:
            print(f"No reminder with id {force_id!r}", file=sys.stderr)
            return 1
        for reminder in targets:
            try:
                send_reminder(reminder, dry_run=dry_run)
                print(f"sent (forced): {reminder.title}")
                sent_count += 1
            except DiscordError as exc:
                print(f"error: {reminder.title}: {exc}", file=sys.stderr)
                errors += 1
        return 1 if errors else 0

    now = local_now("UTC")
    due = due_reminders(
        reminders,
        state,
        now=now,
        ignore_preferred_time=ignore_preferred_time,
    )

    if not due:
        print("No reminders due.")
        return 0

    for reminder, on in due:
        try:
            send_reminder(reminder, dry_run=dry_run)
            if not dry_run:
                mark_sent(state, reminder, on)
            print(f"sent: {reminder.title} ({on.isoformat()})")
            sent_count += 1
        except DiscordError as exc:
            print(f"error: {reminder.title}: {exc}", file=sys.stderr)
            errors += 1

    if sent_count and not dry_run:
        save_state(state, state_path)

    print(f"Done. sent={sent_count} errors={errors}")
    return 1 if errors else 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="remindud",
        description="Send due calendar reminders to Discord.",
    )
    parser.add_argument(
        "--reminders",
        type=Path,
        default=REMINDERS_PATH,
        help="Path to reminders.yaml",
    )
    parser.add_argument(
        "--state",
        type=Path,
        default=STATE_PATH,
        help="Path to state.json",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be sent without calling Discord",
    )
    parser.add_argument(
        "--ignore-preferred-time",
        action="store_true",
        help="Send as soon as the calendar day matches, ignoring preferred_time",
    )
    parser.add_argument(
        "--force",
        metavar="ID",
        help="Force-send a single reminder by id (ignores schedule/state)",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    code = run(
        reminders_path=args.reminders,
        state_path=args.state,
        dry_run=args.dry_run,
        ignore_preferred_time=args.ignore_preferred_time,
        force_id=args.force,
    )
    raise SystemExit(code)


if __name__ == "__main__":
    main()
