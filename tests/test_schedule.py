"""Unit tests for schedule evaluation."""

from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from remindud.models import (
    IntervalSchedule,
    Reminder,
    SentState,
    TimesPerWeekSchedule,
    Weekday,
    WeekdaySchedule,
)
from remindud.runner import already_sent, due_reminders, mark_sent
from remindud.schedule import is_due_on, past_preferred_time


def test_weekdays_due() -> None:
    r = Reminder(
        title="t",
        message="m",
        schedule=WeekdaySchedule(days=[Weekday.MON, Weekday.WED]),
    )
    assert is_due_on(r, date(2026, 8, 3))  # Monday
    assert not is_due_on(r, date(2026, 8, 4))  # Tuesday
    assert is_due_on(r, date(2026, 8, 5))  # Wednesday


def test_interval_every_other_day() -> None:
    r = Reminder(
        title="t",
        message="m",
        schedule=IntervalSchedule(every_n_days=2, start_date=date(2026, 8, 5)),
    )
    assert is_due_on(r, date(2026, 8, 5))
    assert not is_due_on(r, date(2026, 8, 6))
    assert is_due_on(r, date(2026, 8, 7))
    assert not is_due_on(r, date(2026, 8, 4))


def test_times_per_week() -> None:
    r = Reminder(
        title="t",
        message="m",
        schedule=TimesPerWeekSchedule(times=2, days=[Weekday.TUE, Weekday.THU]),
    )
    assert is_due_on(r, date(2026, 8, 4))  # Tue
    assert is_due_on(r, date(2026, 8, 6))  # Thu
    assert not is_due_on(r, date(2026, 8, 5))


def test_preferred_time_gate() -> None:
    r = Reminder(
        title="t",
        message="m",
        schedule=WeekdaySchedule(days=[Weekday.WED]),
        preferred_time=time(9, 0),
        timezone="America/Sao_Paulo",
    )
    tz = ZoneInfo("America/Sao_Paulo")
    before = datetime(2026, 8, 5, 8, 0, tzinfo=tz)
    after = datetime(2026, 8, 5, 9, 0, tzinfo=tz)
    assert not past_preferred_time(r, before)
    assert past_preferred_time(r, after)


def test_dedupe_state() -> None:
    r = Reminder(
        id="abc",
        title="t",
        message="m",
        schedule=WeekdaySchedule(days=list(Weekday)),
        preferred_time=time(0, 0),
        timezone="UTC",
    )
    state = SentState()
    now = datetime(2026, 8, 5, 12, 0, tzinfo=ZoneInfo("UTC"))
    due = due_reminders([r], state, now=now)
    assert len(due) == 1
    mark_sent(state, r, date(2026, 8, 5))
    assert already_sent(state, r, date(2026, 8, 5))
    assert due_reminders([r], state, now=now) == []
