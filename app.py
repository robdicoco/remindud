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
from remindud.store import (
    delete_reminder,
    get_reminder,
    load_reminders,
    upsert_reminder,
)

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

KIND_LABELS = ["Weekdays", "Every N days", "Times per week"]
KIND_FROM_SCHEDULE = {
    "weekdays": "Weekdays",
    "interval": "Every N days",
    "times_per_week": "Times per week",
}


def _weekday_multiselect(
    label: str,
    *,
    default: list[Weekday],
    key: str,
) -> list[Weekday]:
    return st.multiselect(
        label,
        options=list(Weekday),
        default=default,
        format_func=lambda d: WEEKDAY_LABELS[d],
        key=key,
    )


def _timezone_options(current: str | None = None) -> list[str]:
    zones = list(COMMON_TIMEZONES)
    if current and current not in zones:
        zones.insert(0, current)
    return zones


def _schedule_fields(
    *,
    prefix: str,
    kind: str,
    existing: Reminder | None,
) -> WeekdaySchedule | IntervalSchedule | TimesPerWeekSchedule | None:
    if kind == "Weekdays":
        default_days = (
            list(existing.schedule.days)
            if existing and isinstance(existing.schedule, WeekdaySchedule)
            else [Weekday.MON, Weekday.WED, Weekday.FRI]
        )
        days = _weekday_multiselect(
            "Weekdays",
            default=default_days,
            key=f"{prefix}-weekdays",
        )
        if not days:
            st.warning("Pick at least one weekday.")
            return None
        return WeekdaySchedule(days=days)

    if kind == "Every N days":
        default_every = (
            existing.schedule.every_n_days
            if existing and isinstance(existing.schedule, IntervalSchedule)
            else 2
        )
        default_start = (
            existing.schedule.start_date
            if existing and isinstance(existing.schedule, IntervalSchedule)
            else datetime.now(tz=ZoneInfo("UTC")).date()
        )
        every = st.number_input(
            "Every N days",
            min_value=1,
            max_value=365,
            value=int(default_every),
            key=f"{prefix}-every",
        )
        start = st.date_input(
            "Start date (anchor)",
            value=default_start,
            key=f"{prefix}-start",
        )
        return IntervalSchedule(every_n_days=int(every), start_date=start)

    default_times = (
        existing.schedule.times
        if existing and isinstance(existing.schedule, TimesPerWeekSchedule)
        else 2
    )
    default_days = (
        list(existing.schedule.days)
        if existing and isinstance(existing.schedule, TimesPerWeekSchedule)
        else [Weekday.TUE, Weekday.THU][: int(default_times)]
    )
    times = st.number_input(
        "Times per week",
        min_value=1,
        max_value=7,
        value=int(default_times),
        key=f"{prefix}-times",
    )
    days = _weekday_multiselect(
        f"Pick exactly {int(times)} weekday(s)",
        default=default_days,
        key=f"{prefix}-tpw-days",
    )
    if len(days) != int(times):
        st.warning(f"Select exactly {int(times)} distinct weekdays.")
        return None
    return TimesPerWeekSchedule(times=int(times), days=days)


def render_editor(existing: Reminder | None = None) -> None:
    editing = existing is not None
    prefix = f"edit-{existing.id}" if editing else "create"
    st.subheader("Edit reminder" if editing else "New reminder")

    if editing:
        st.caption(f"Editing `{existing.id}`")

    title = st.text_input(
        "Title",
        value=existing.title if editing else "",
        placeholder="Take vitamins",
        key=f"{prefix}-title",
    )
    message = st.text_area(
        "Discord message",
        value=existing.message if editing else "",
        placeholder="Don't forget your vitamins today!",
        height=100,
        key=f"{prefix}-message",
    )

    default_kind = (
        KIND_FROM_SCHEDULE[existing.schedule.kind] if editing else "Weekdays"
    )
    kind = st.selectbox(
        "Schedule type",
        KIND_LABELS,
        index=KIND_LABELS.index(default_kind),
        help=(
            "Weekdays — fire on chosen days each week. "
            "Every N days — e.g. every other day from an anchor date. "
            "Times per week — pick N specific weekdays."
        ),
        key=f"{prefix}-kind",
    )
    schedule = _schedule_fields(prefix=prefix, kind=kind, existing=existing)

    zones = _timezone_options(existing.timezone if editing else None)
    default_tz = existing.timezone if editing else "America/Sao_Paulo"
    default_time = existing.preferred_time if editing else time(9, 0)
    default_enabled = existing.enabled if editing else True

    c1, c2 = st.columns(2)
    preferred = c1.time_input(
        "Preferred time",
        value=default_time,
        key=f"{prefix}-time",
    )
    timezone = c2.selectbox(
        "Timezone",
        zones,
        index=zones.index(default_tz),
        key=f"{prefix}-tz",
    )
    enabled = st.checkbox("Enabled", value=default_enabled, key=f"{prefix}-enabled")

    actions = st.columns([1, 1, 4] if editing else [1, 5])
    save_label = "Save changes" if editing else "Add reminder"
    if actions[0].button(save_label, type="primary", key=f"{prefix}-save"):
        if not title.strip() or not message.strip():
            st.error("Title and message are required.")
        elif schedule is None:
            st.error("Fix the schedule before saving.")
        else:
            fields = {
                "title": title.strip(),
                "message": message.strip(),
                "enabled": enabled,
                "schedule": schedule,
                "preferred_time": preferred,
                "timezone": timezone,
            }
            reminder = (
                existing.model_copy(update=fields)
                if editing
                else Reminder(**fields)
            )
            upsert_reminder(reminder)
            st.session_state.pop("editing_id", None)
            st.success(f"Saved “{reminder.title}” ({reminder.id})")
            st.rerun()

    if editing and actions[1].button("Cancel", key=f"{prefix}-cancel"):
        st.session_state.pop("editing_id", None)
        st.rerun()


def render_list() -> None:
    reminders = load_reminders()
    st.subheader("Your reminders")
    if not reminders:
        st.info("No reminders yet. Create one below.")
        return

    for reminder in reminders:
        nxt = next_occurrence(reminder)
        with st.container(border=True):
            cols = st.columns([4, 1, 1, 1])
            status = "on" if reminder.enabled else "off"
            cols[0].markdown(
                f"**{reminder.title}**  \n"
                f"{reminder.message}  \n"
                f"`{reminder.schedule_summary()}` · "
                f"{format_preferred_time(reminder.preferred_time)} {reminder.timezone} · "
                f"next: {nxt.isoformat() if nxt else '—'} · *{status}*"
            )
            if cols[1].button("Edit", key=f"edit-btn-{reminder.id}"):
                st.session_state.editing_id = reminder.id
                st.rerun()
            if cols[2].button("Toggle", key=f"toggle-{reminder.id}"):
                reminder.enabled = not reminder.enabled
                upsert_reminder(reminder)
                st.rerun()
            if cols[3].button("Delete", key=f"del-{reminder.id}", type="primary"):
                if st.session_state.get("editing_id") == reminder.id:
                    st.session_state.pop("editing_id", None)
                delete_reminder(reminder.id)
                st.rerun()


def main() -> None:
    st.title("Remindud")
    st.caption("Calendar reminders → Discord webhook. Edit here; send only when you run the sender.")
    render_list()
    st.divider()

    editing_id = st.session_state.get("editing_id")
    existing = get_reminder(editing_id) if editing_id else None
    if editing_id and existing is None:
        st.session_state.pop("editing_id", None)
        existing = None
    render_editor(existing)

    with st.expander("How delivery works"):
        st.markdown(
            """
1. Save reminders here (writes `data/reminders.yaml`).
2. Commit & push the file.
3. Delivery is **manual** — run `uv run remindud` locally, or start the GitHub Actions workflow yourself. There is no scheduled autorun.
4. `data/state.json` records the last send date so each reminder fires at most once per day.
            """
        )


if __name__ == "__main__":
    main()
