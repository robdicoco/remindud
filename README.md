# Remindud

Calendar reminders delivered to Discord via webhook.

Configure events in a Streamlit UI (or by editing YAML). Delivery runs in the background — locally with `uv run remindud`, or on a schedule with GitHub Actions twice a day.

## Features

- **Weekdays** — e.g. Mon / Wed / Fri
- **Every N days** — e.g. every other day from an anchor date
- **Times per week** — e.g. twice a week on Tue & Thu
- Preferred local time + timezone per reminder
- Deduped sends via `data/state.json` (at most once per calendar day)

## Setup

```bash
uv sync
```

Create a Discord webhook (channel settings → Integrations → Webhooks) and export it:

```bash
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
```

Or copy `.env.example` to `.env` for local use (do not commit the real URL).

### Configure reminders (Streamlit)

```bash
uv run streamlit run app.py
```

This writes `data/reminders.yaml`. Commit and push so Actions can see your events.

Example reminders ship disabled in `data/reminders.yaml` — enable or replace them.

### Run the sender (background)

```bash
# See what would send today
uv run remindud --dry-run

# Send due reminders
uv run remindud

# Force one reminder by id
uv run remindud --force example-vitamins
```

## GitHub Actions

Workflow: `.github/workflows/remind.yml`

- Cron: **11:00 UTC** and **20:00 UTC** (twice daily)
- Manual run: Actions → Remindud → Run workflow
- After a successful send, updated `data/state.json` is committed back so the next run does not double-send

Add the repository secret:

| Secret | Value |
|--------|--------|
| `DISCORD_WEBHOOK_URL` | your Discord webhook URL |

## Data layout

```
data/
  reminders.yaml   # schedules (edit via Streamlit or by hand)
  state.json       # last_sent dates (managed by the runner)
```

## Schedule notes

Actions may run before a reminder’s `preferred_time`. That run skips it; the later daily run picks it up once the preferred time has passed. Use `--ignore-preferred-time` (or the workflow input) to send as soon as the calendar day matches.
