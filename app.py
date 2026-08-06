"""Streamlit setup UI for Remindud calendar reminders."""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

import streamlit as st

from remindud.models import (
    WEEKDAY_LABELS,
    IntervalSchedule,
    Reminder,
    TimesPerWeekSchedule,
    Weekday,
    WeekdaySchedule,
)
from remindud.schedule import format_preferred_time, next_occurrence
from remindud.store import delete_reminder, load_reminders, upsert_reminder

st.set_page_config(page_title="Remindud", page_icon="📅", layout="centered")

COMMON_TIMEZONES = [
    "UTC",
    "America/Sao_Paulo",
    "America/New_York",
    "America/Chicago",
    "America/Los_Angeles",
    "Europe/London",
    "Europe/Berlin",
    "Europe/Lisbon",
    "Asia/Tokyo",
]


def _weekday_multiselect(
    label: str,
    default: list[Weekday] | None = None,
    key: str = "weekdays",
) -> list[Weekday]:
    options = list(Weekday)
    default = default or []
    return st.multiselect(
        label,
        options=options,
        default=default,
        format_func=lambda d: WEEKDAY_LABELS[d],
        key=key,
    )


def render_list() -> None:
    reminders = load_reminders()
    st.subheader("Your reminders")
    if not reminders:
        st.info("No reminders yet. Create one below.")
        return

    for reminder in reminders:
        nxt = next_occurrence(reminder)
        with st.container(border=True):
            cols = st.columns([4, 1, 1])
            status = "on" if reminder.enabled else "off"
            cols[0].markdown(
                f"**{reminder.title}**  \n"
                f"{reminder.message}  \n"
                f"`{reminder.schedule_summary()}` · "
                f"{format_preferred_time(reminder.preferred_time)} {reminder.timezone} · "
                f"next: {nxt.isoformat() if nxt else '—'} · *{status}*"
            )
            if cols[1].button("Toggle", key=f"toggle-{reminder.id}"):
                reminder.enabled = not reminder.enabled
                upsert_reminder(reminder)
                st.rerun()
            if cols[2].button("Delete", key=f"del-{reminder.id}", type="primary"):
                delete_reminder(reminder.id)
                st.rerun()


def render_create() -> None:
    st.subheader("New reminder")

    title = st.text_input("Title", placeholder="Take vitamins")
    message = st.text_area(
        "Discord message",
        placeholder="Don't forget your vitamins today!",
        height=100,
    )

    kind = st.selectbox(
        "Schedule type",
        ["Weekdays", "Every N days", "Times per week"],
        help=(
            "Weekdays — fire on chosen days each week. "
            "Every N days — e.g. every other day from an anchor date. "
            "Times per week — pick N specific weekdays."
        ),
    )

    schedule = None
    if kind == "Weekdays":
        days = _weekday_multiselect(
            "Weekdays",
            default=[Weekday.MON, Weekday.WED, Weekday.FRI],
            key="create-weekdays",
        )
        if days:
            schedule = WeekdaySchedule(days=days)
        else:
            st.warning("Pick at least one weekday.")
    elif kind == "Every N days":
        every = st.number_input("Every N days", min_value=1, max_value=365, value=2)
        start = st.date_input(
            "Start date (anchor)",
            value=datetime.now(tz=ZoneInfo("UTC")).date(),
        )
        schedule = IntervalSchedule(every_n_days=int(every), start_date=start)
    else:
        times = st.number_input("Times per week", min_value=1, max_value=7, value=2)
        days = _weekday_multiselect(
            f"Pick exactly {int(times)} weekday(s)",
            default=[Weekday.TUE, Weekday.THU][: int(times)],
            key="create-tpw-days",
        )
        if len(days) == int(times):
            schedule = TimesPerWeekSchedule(times=int(times), days=days)
        else:
            st.warning(f"Select exactly {int(times)} distinct weekdays.")

    c1, c2 = st.columns(2)
    preferred = c1.time_input("Preferred time", value=time(9, 0))
    timezone = c2.selectbox("Timezone", COMMON_TIMEZONES, index=1)
    enabled = st.checkbox("Enabled", value=True)

    if st.button("Add reminder", type="primary"):
        if not title.strip() or not message.strip():
            st.error("Title and message are required.")
        elif schedule is None:
            st.error("Fix the schedule before saving.")
        else:
            reminder = Reminder(
                title=title.strip(),
                message=message.strip(),
                enabled=enabled,
                schedule=schedule,
                preferred_time=preferred,
                timezone=timezone,
            )
            upsert_reminder(reminder)
            st.success(f"Saved “{reminder.title}” ({reminder.id})")
            st.rerun()


def main() -> None:
    st.title("Remindud")
    st.caption("Calendar reminders → Discord webhook. Edit here; GitHub Actions sends them.")
    render_list()
    st.divider()
    render_create()
    with st.expander("How delivery works"):
        st.markdown(
            """
1. Save reminders here (writes `data/reminders.yaml`).
2. Commit & push the file.
3. GitHub Actions runs **twice daily**, checks schedules, and posts to your Discord webhook.
4. `data/state.json` records the last send date so each reminder fires at most once per day.
            """
        )


if __name__ == "__main__":
    main()
