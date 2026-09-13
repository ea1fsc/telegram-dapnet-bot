# How it works

This page explains the moving parts for operators and curious users. For day-to-day steps see the [user guide](user-guide.md).

## High-level loop

```
Telegram long polling
        │
        ├─ commands / buttons  →  SQLite (users, calendars, rics, …)
        │
        ├─ Job “caldav-sync”   every SYNC_INTERVAL_SECONDS (default 600)
        │         first run ~10 s after start
        │         approved users, enabled calendars only
        │         window: now − 1 hour  …  now + FETCH_EVENT_WINDOW_DAYS
        │         writes event_cache
        │
        └─ Job “dapnet-dispatch” every DISPATCH_INTERVAL_SECONDS (default 60)
                  first run ~20 s after start
                  for each cached event and each reminder offset:
                    if due within MISFIRE_GRACE_MINUTES and not yet in sent_reminders:
                      POST DAPNET /calls
                      send Telegram reminder
                      mark sent if at least one of the two succeeded
```

There is **no** CalDAV webhook and **no** Telegram webhook. Both sides are poll-based.

JobQueue is **not** persisted. After a restart, jobs start again from “first = 10/20 seconds”. Duplicate pages are prevented by `sent_reminders` (unique on user + event uid + recurrence start + offset) and by skipping due times older than the grace window.

## Reminder offsets

```
offsets = equally spaced from lead_minutes down, then always 0 (event start)
```

| Lead | Repeats | Alerts |
| --- | --- | --- |
| 60 min | 1 | T-60, T-0 |
| 60 min | 3 | T-60, T-40, T-20, T-0 |
| 1440 min (1 day) | 2 | T-1440, T-720, T-0 |

All-day events use **09:00** in the user’s IANA timezone as T-0.

## DAPNET page format

API **1.1** `POST /calls`:

```json
{
  "text": "EA1XXX: Meeting 07/09 18:00",
  "callSignNames": ["ea1xxx", "ea4hqf"],
  "transmitterGroupNames": ["all", "ea-all"],
  "emergency": false
}
```

- `text` is truncated to 80 characters.
- Prefix is the **user’s** DAPNET callsign (sanitised, upper case), not the operator callsign.
- Body is the event summary (accents / `¿¡` / some punctuation stripped) plus `dd/mm` or `dd/mm HH:MM`.
- `callSignNames` are unique **enabled RIC owner callsigns**. If the user has no RIC rows, the page goes to their own callsign. If they have rows but all are OFF, send is skipped (`No DAPNET destinations were selected`).
- `emergency` is always `false`.
- HTTP retries on network errors and on status 429 / 5xx (up to 3 attempts).
- Timeout 20 seconds per request.

Test pages use: `{CALLSIGN}: test telegram-dapnet-bot`.

## Telegram reminder text

Plain text, roughly:

- header (“Upcoming event in 1 hour” or “Event starting now”);
- summary (clipped);
- when / where / timezone;
- “DAPNET page sent to …” plus the 80-character text, **or** a line that DAPNET failed but Telegram still delivered.

## Calendar sync details

- Library: `python-caldav` `search(..., event=True, expand=True)`.
- Recurring instances are stored as one `event_cache` row each (`uid` + `recurrence_start`).
- `STATUS:CANCELLED` is dropped.
- Events without a UID are dropped.
- Turning a calendar **OFF** deletes its cached events (so they will not page).
- If CalDAV auth or network fails during the background sync, the user gets a Telegram error (not a pager message): *I could not read your Nextcloud calendars…*
- `/refresh` reports how many calendars synced, names that failed, and up to 15 upcoming events.

This is **not** instant. Default poll is 10 minutes. Very last-minute events may miss the first lead offset if they appear after that offset’s fire time; later offsets (including T-0) can still fire if the event is in cache and within grace.

## Failure and retry

| DAPNET | Telegram | Result |
| --- | --- | --- |
| OK | OK | Marked sent |
| Fail | OK | Marked sent — **no DAPNET retry** for that offset |
| OK | Fail | Marked sent |
| Fail | Fail | Not marked; next dispatch cycle retries while still inside `MISFIRE_GRACE_MINUTES` |

## RIC catalog

Tables:

- `rics` — shared map `ric → callsign` (survives `/delete`);
- `user_rics` — per-user enable/disable and source (`radioid`, `dapnet`, `catalog`, `manual`).

On startup, CSV values in `users.dapnet_rics` are backfilled into `user_rics` if needed.

RadioID: `https://radioid.net/api/dmr/user/?callsign=…`. Network errors do **not** block registration; you simply get fewer suggestions. DMR IDs above 2097151 lose the first digit to fit POCSAG (same rule as historic PagerBot).

## Project modules (operators / developers)

```
src/telegram_dapnet_bot/
  main.py              # Application, JobQueue
  config.py            # pydantic-settings
  crypto.py            # Fernet
  bot/                 # Telegram handlers
  db/                  # models, repo, SQLite
  services/            # DAPNET, CalDAV, RadioID, reminders, format
tests/
```

Entry point: `python -m telegram_dapnet_bot` → `main()`.
