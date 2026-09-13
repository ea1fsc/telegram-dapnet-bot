# Limitations

Honest list of what version **0.1.0** does not do, and behavioural constraints that surprise people. Feature requests belong in the project tracker, not in `.env`.

## Out of scope (not implemented)

- No `/send`, ad-hoc page composer, or club **broadcast**.
- No POCSAG **listener** (the bot does not receive pages).
- No configurable **page templates** (format is fixed, 80 characters).
- No extra “**Telegram only**” reminder channel; DAPNET and Telegram share the same offsets.
- **SQLite only** — no PostgreSQL, MySQL, or Redis.
- **No CalDAV push / webhooks** — calendars are polled (`SYNC_INTERVAL_SECONDS`, default 10 minutes).
- **No Alembic** — schema changes are `create_all` plus a couple of `ALTER TABLE`s.
- **No i18n** — Telegram UI is English only.
- **No Telegram webhooks** — long polling only.
- **No group-chat** workflow, topics, or channel posting.
- `PagerBot/` in the repository is **reference**, not a supported second product.

## DAPNET API 1.1 constraints

- You cannot address a **single RIC** when several pagers share one callsign. `POST /calls` uses `callSignNames`; DAPNET delivers to **all** pagers of that callsign.
- There is no “send to this RIC number” field. The bot’s RIC list is a map onto callsigns.
- An **invalid transmitter group** name can cause DAPNET to drop the **whole** call.
- User lookup during `/register` uses `DAPNET_DEFAULT_SERVER` (usually Germany), **not** the Spain/Germany button the user just tapped for sending. A callsign that exists only on the other core may fail registration.
- The `pagers` array on `GET /callSigns/{cs}` is often **hidden** for non-admin operators. Existence of the user + subscriber is then enough; RadioID and manual RIC entry identify pagers.
- API **2.0** is not supported.

## Reminder behaviour

- If DAPNET fails but Telegram succeeds, that offset is **marked sent** — **no DAPNET retry**.
- After a process crash, only reminders still inside `MISFIRE_GRACE_MINUTES` (default 30) are sent. Longer outages skip old due times on purpose (no flood).
- JobQueue is in-memory; restart does not restore “next run in 3 minutes” — intervals start again after 10/20 seconds.
- Events created **after** a lead offset has passed will not get that offset (the fire time is already in the past and may be outside grace). Later offsets can still fire.
- Recurrence expansion depends on **python-caldav 3.x** `search(..., expand=True)`. Odd CalDAV servers may return unexpanded or incomplete series.
- All-day events always use **09:00** local; you cannot choose another hour.
- Lead times are a **fixed set** (15 / 30 / 60 / 180 / 1440 / 10080 minutes), not an arbitrary number.
- `/refresh` lists at most **15** upcoming events in the reply; more still sit in the cache.

## Product / scale limits

- `/users` lists at most **50** people.
- RIC picker buttons show at most **12** rows; TX group buttons at most **18** names (commands still work).
- One Telegram user id → one bot account (no multiple Nextcloud profiles per Telegram user).
- Registration and add-RIC conversations time out after **600 seconds**.
- Background CalDAV errors notify the user in Telegram; they do not page the operator.
- No dashboard, metrics, or health HTTP endpoint.
- No automatic database backup.
- Callsign pattern is `3–20` of `[a-z0-9/]` — unusual callsign punctuation is rejected.

## Security / ops

- Fernet key loss = stored Nextcloud passwords unreadable.
- Admins see Nextcloud URL + username on signup (not the password).
- Plain-text Telegram (by design).
- SQLite file is the entire state; concurrent hosts pointing at the same DB file over NFS are unsupported.

## Comparison with historic PagerBot

The rewrite does **not** aim for feature-parity with `PagerBot/`. Missing on purpose: free-form send, listener-side features, and anything that is not “calendar → approved user → DAPNET + Telegram reminder”.
