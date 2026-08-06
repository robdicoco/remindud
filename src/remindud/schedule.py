"""Schedule evaluation — is a reminder due on a given date?"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from remindud.models import (
    IntervalSchedule,
    Reminder,
    TimesPerWeekSchedule,
    Weekday,
    WeekdaySchedule,
)


def weekday_of(d: date) -> Weekday:
    return list(Weekday)[d.weekday()]


def is_due_on(reminder: Reminder, on: date) -> bool:
    """Return True if the reminder's schedule matches the calendar date."""
    schedule = reminder.schedule

    if isinstance(schedule, WeekdaySchedule):
        return weekday_of(on) in schedule.days

    if isinstance(schedule, TimesPerWeekSchedule):
        return weekday_of(on) in schedule.days

    if isinstance(schedule, IntervalSchedule):
        if on < schedule.start_date:
            return False
        delta = (on - schedule.start_date).days
        return delta % schedule.every_n_days == 0

    return False


def local_now(tz_name: str) -> datetime:
    return datetime.now(ZoneInfo(tz_name))


def local_today(tz_name: str) -> date:
    return local_now(tz_name).date()


def past_preferred_time(reminder: Reminder, now: datetime | None = None) -> bool:
    """
    True once today's preferred_time has passed in the reminder's timezone.

    GitHub Actions may run twice a day; the morning run skips if preferred
    time has not arrived yet, the afternoon run catches anything still due.
    """
    tz = ZoneInfo(reminder.timezone)
    current = now.astimezone(tz) if now else datetime.now(tz)
    preferred = datetime.combine(current.date(), reminder.preferred_time, tzinfo=tz)
    return current >= preferred


def next_occurrence(reminder: Reminder, after: date | None = None) -> date | None:
    """Find the next date the reminder fires on (inclusive of `after`)."""
    start = after or local_today(reminder.timezone)
    for offset in range(366 * 2):
        candidate = start + timedelta(days=offset)
        if is_due_on(reminder, candidate):
            return candidate
    return None


def format_preferred_time(t: time) -> str:
    return t.strftime("%H:%M")
