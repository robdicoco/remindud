"""Persistence for reminders and send state."""

from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import ValidationError

from remindud.models import Reminder, ReminderStore, SentState

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
REMINDERS_PATH = DATA_DIR / "reminders.yaml"
STATE_PATH = DATA_DIR / "state.json"


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def load_reminders(path: Path = REMINDERS_PATH) -> list[Reminder]:
    if not path.exists():
        return []
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    store = ReminderStore.model_validate(raw)
    return store.reminders


def save_reminders(reminders: list[Reminder], path: Path = REMINDERS_PATH) -> None:
    ensure_data_dir()
    store = ReminderStore(reminders=reminders)
    payload = store.model_dump(mode="json")
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def load_state(path: Path = STATE_PATH) -> SentState:
    if not path.exists():
        return SentState()
    try:
        return SentState.model_validate_json(path.read_text(encoding="utf-8"))
    except (ValidationError, ValueError):
        return SentState()


def save_state(state: SentState, path: Path = STATE_PATH) -> None:
    ensure_data_dir()
    path.write_text(state.model_dump_json(indent=2) + "\n", encoding="utf-8")


def get_reminder(reminder_id: str, path: Path = REMINDERS_PATH) -> Reminder | None:
    for reminder in load_reminders(path):
        if reminder.id == reminder_id:
            return reminder
    return None


def upsert_reminder(reminder: Reminder, path: Path = REMINDERS_PATH) -> None:
    reminders = load_reminders(path)
    for i, existing in enumerate(reminders):
        if existing.id == reminder.id:
            reminders[i] = reminder
            save_reminders(reminders, path)
            return
    reminders.append(reminder)
    save_reminders(reminders, path)


def delete_reminder(reminder_id: str, path: Path = REMINDERS_PATH) -> bool:
    reminders = load_reminders(path)
    filtered = [r for r in reminders if r.id != reminder_id]
    if len(filtered) == len(reminders):
        return False
    save_reminders(filtered, path)
    return True
