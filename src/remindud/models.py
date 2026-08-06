"""Reminder data models."""

from __future__ import annotations

from datetime import date, time
from enum import StrEnum
from typing import Annotated, Literal
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator, model_validator


class Weekday(StrEnum):
    MON = "mon"
    TUE = "tue"
    WED = "wed"
    THU = "thu"
    FRI = "fri"
    SAT = "sat"
    SUN = "sun"


WEEKDAY_INDEX: dict[Weekday, int] = {
    Weekday.MON: 0,
    Weekday.TUE: 1,
    Weekday.WED: 2,
    Weekday.THU: 3,
    Weekday.FRI: 4,
    Weekday.SAT: 5,
    Weekday.SUN: 6,
}

WEEKDAY_LABELS: dict[Weekday, str] = {
    Weekday.MON: "Monday",
    Weekday.TUE: "Tuesday",
    Weekday.WED: "Wednesday",
    Weekday.THU: "Thursday",
    Weekday.FRI: "Friday",
    Weekday.SAT: "Saturday",
    Weekday.SUN: "Sunday",
}


class WeekdaySchedule(BaseModel):
    """Fire on specific weekdays (e.g. Mon/Wed/Fri)."""

    kind: Literal["weekdays"] = "weekdays"
    days: list[Weekday] = Field(min_length=1)

    @field_validator("days")
    @classmethod
    def unique_days(cls, value: list[Weekday]) -> list[Weekday]:
        seen: set[Weekday] = set()
        unique: list[Weekday] = []
        for day in value:
            if day not in seen:
                seen.add(day)
                unique.append(day)
        return unique


class IntervalSchedule(BaseModel):
    """Fire every N days from an anchor date (e.g. every other day)."""

    kind: Literal["interval"] = "interval"
    every_n_days: Annotated[int, Field(ge=1)] = 2
    start_date: date


class TimesPerWeekSchedule(BaseModel):
    """Fire a fixed number of times per week on chosen weekdays."""

    kind: Literal["times_per_week"] = "times_per_week"
    times: Annotated[int, Field(ge=1, le=7)] = 2
    days: list[Weekday] = Field(min_length=1)

    @model_validator(mode="after")
    def days_match_times(self) -> TimesPerWeekSchedule:
        unique = list(dict.fromkeys(self.days))
        if len(unique) != self.times:
            raise ValueError(
                f"times_per_week expects {self.times} distinct weekdays, got {len(unique)}"
            )
        self.days = unique
        return self


Schedule = Annotated[
    WeekdaySchedule | IntervalSchedule | TimesPerWeekSchedule,
    Field(discriminator="kind"),
]


class Reminder(BaseModel):
    id: str = Field(default_factory=lambda: uuid4().hex[:12])
    title: str = Field(min_length=1)
    message: str = Field(min_length=1)
    enabled: bool = True
    schedule: Schedule
    # Preferred local time of day (runner still fires once per matching calendar day).
    preferred_time: time = time(9, 0)
    timezone: str = "UTC"

    def schedule_summary(self) -> str:
        s = self.schedule
        if isinstance(s, WeekdaySchedule):
            days = ", ".join(WEEKDAY_LABELS[d] for d in s.days)
            return f"Weekdays: {days}"
        if isinstance(s, IntervalSchedule):
            unit = "day" if s.every_n_days == 1 else "days"
            return f"Every {s.every_n_days} {unit} from {s.start_date.isoformat()}"
        days = ", ".join(WEEKDAY_LABELS[d] for d in s.days)
        return f"{s.times}× / week ({days})"


class ReminderStore(BaseModel):
    reminders: list[Reminder] = Field(default_factory=list)


class SentState(BaseModel):
    """Tracks the last calendar date a reminder was successfully sent."""

    last_sent: dict[str, date] = Field(default_factory=dict)
