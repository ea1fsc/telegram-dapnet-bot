# telegram-dapnet-bot

Telegram bot that reads each user’s Nextcloud calendars (any instance) and sends reminder pages on [DAPNET](https://hampager.de/) using **your operator account**. Recipients are the DAPNET callsigns behind the RICs the user selected.

An administrator must approve every registration. The Telegram UI is English, plain text (no Markdown). Package version **0.1.0**. License **GPL-3.0-or-later**.

This is not a free-form paging messenger. `PagerBot/` in this repo is **reference only** (historical `bot47.py`). Do not copy `/send`, POCSAG listeners, Postgres, i18n, or gifs from it.

## How it works

1. A ham registers in Telegram: DAPNET callsign, Spain/Germany core, destination RICs, Nextcloud URL + username + app password.
2. An admin approves (or rejects) the request.
3. The user turns calendars **ON** and sets reminder lead time, timezone, and transmitter groups.
4. A background job polls CalDAV. Another job sends due reminders as:
   - a DAPNET `POST /calls` page (max 80 characters, sanitised), and
   - a Telegram message with the same event.

Auth for DAPNET is always the **operator** credentials in `.env`. The page goes to the **callsigns of the user’s enabled RICs** (DAPNET API 1.1 has no “send to this RIC number” field).

```
Telegram user  →  Nextcloud CalDAV (their instance)
                     ↓ poll every 10 min
                 event cache (SQLite)
                     ↓ every 60 s
         DAPNET page + Telegram reminder
```

## Prerequisites

**Operator (you, running the bot)**

- Python 3.12+ (or Docker)
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- Your numeric Telegram user id (for example [@userinfobot](https://t.me/userinfobot))
- A DAPNET operator account (callsign + password) that can `POST /calls`

**Each end user**

- A DAPNET user whose callsign exists and has a subscriber (RIC)
- Nextcloud (or compatible CalDAV) with an **app password**  
  Settings → Security. Do not use the main password if 2FA is on.

## Operator setup (step by step)

### 1. Clone and create a virtualenv

```bash
cd telegram-dapnet-bot
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### 2. Copy environment file

```bash
cp .env.example .env
```

Never commit `.env`. It holds tokens and passwords.

### 3. Generate an encryption key

Nextcloud app passwords are stored with Fernet:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Paste the result into `ENCRYPTION_KEY`. If you lose this key, existing Nextcloud passwords in the database cannot be decrypted; users must `/register` again.

### 4. Fill `.env`

Required:

| Variable | Meaning |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | From BotFather |
| `ADMIN_TELEGRAM_IDS` | Comma-separated Telegram user ids that can approve people |
| `DAPNET_CALLSIGN` | Operator callsign used as HTTP Basic user |
| `DAPNET_PASSWORD` | Operator DAPNET password |
| `ENCRYPTION_KEY` | Fernet key from step 3 |

Common optionals (defaults in `.env.example`):

| Variable | Default | Meaning |
| --- | --- | --- |
| `DAPNET_API_URL` | `https://hampager.de/api` | Germany core (API 1.1) |
| `DAPNET_API_URL_ES` | `http://dapnet.es:8080` | Spain core |
| `DAPNET_DEFAULT_TX_GROUP` | `all` | Initial transmitter group for new users |
| `DAPNET_DEFAULT_SERVER` | `de` | Initial core (`de` / `es`) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/bot.db` | SQLite file |
| `SYNC_INTERVAL_SECONDS` | `600` | CalDAV poll interval |
| `DISPATCH_INTERVAL_SECONDS` | `60` | Reminder send interval |
| `FETCH_EVENT_WINDOW_DAYS` | `14` | How far ahead to fetch events |
| `MISFIRE_GRACE_MINUTES` | `30` | Still send a due reminder if the bot was down |
| `DEFAULT_TIMEZONE` | `Europe/Madrid` | New-user timezone |
| `DEFAULT_LEAD_MINUTES` | `60` | New-user lead time |
| `DEFAULT_REPEAT_COUNT` | `1` | New-user repeat count (before T-0) |
| `LOG_LEVEL` | `INFO` | Logging level |

### 5. Run the bot

```bash
python -m telegram_dapnet_bot
```

On first start it creates `./data/bot.db` (or whatever `DATABASE_URL` points to). Talk to the bot in Telegram; `/start` and `/help` show a command menu with buttons.

### 6. Optional: Docker

```bash
cp .env.example .env
# edit .env
docker compose up --build -d
```

SQLite lives in `./data` on the host (`./data:/app/data`).

## End-user setup (step by step)

Everything below is in Telegram. Commands and buttons do the same thing.

### 1. Open the bot and register

Send `/start` or `/register`.

1. **Callsign** — letters/numbers, 3–20 characters. The bot checks DAPNET `GET /users/{cs}` and `GET /callSigns/{cs}`.
2. **Core** — Spain (`dapnet.es`) or Germany (`hampager.de`). This is where **pages are sent**. User lookup during register uses the default API URL (usually Germany).
3. **RICs** — which pagers should get calendar pages:
   - RadioID DMR IDs (mapped into the POCSAG range) appear as ON/OFF buttons
   - Visible DAPNET pagers are offered if the operator account can see them
   - Type a RIC number, or tap **Enter RIC manually**
   - If that RIC is already in this bot’s catalog, its callsign is reused
   - If it is new, send the DAPNET callsign that owns the pager (or tap **Use my callsign**)
   - Tap **Done** when at least one RIC is selected
4. **Nextcloud URL** — any instance. `https://` and `/remote.php/dav` are added if missing. Only `http`/`https`.
5. **Username** and **app password**. The bot tries to delete the password message.

Registration times out after **600 seconds**. `/cancel` aborts.

Until an admin approves you, `/calendars` and the other “approved” commands are blocked. `/status` and `/delete` still work.

### 2. Wait for approval

Admins listed in `ADMIN_TELEGRAM_IDS` get a plain-text notice with Approve / Reject buttons. They can also use `/pending`, `/approve <telegram_id>`, `/reject <telegram_id>`.

If you re-register with the **same** callsign while already approved, you stay approved (credentials update). If you **change** callsign, you go back to pending.

### 3. After approval

1. `/calendars` — turn calendars **ON** (synced + reminded) or **OFF**. **Refresh list** re-reads CalDAV. **Refresh events** reloads upcoming events (same as `/refresh`).
2. `/reminders` — lead time (15 min … 1 week) and 1–3 equally spaced alerts **before** the event, **plus one at event time**.
3. `/txgroup` — transmitter groups (spreads). Presets: `all`, `ea-all`, `dl-all`, `us-all`. Example: `/txgroup ea-all,dl-all`.
4. `/server` — Spain or Germany core for **sending**.
5. `/rics` — add, enable, disable, or remove destination RICs.
6. `/timezone Europe/Madrid` — IANA timezone (used for all-day events and “when”).
7. `/test` — send a test page to the enabled RIC callsigns.
8. `/refresh` — pull events now and list what is coming.

`/help` shows only the commands that apply to your status. Admin commands appear only for admin chats.

### 4. Leave

`/delete` (or `/delete confirm`) wipes your row: Nextcloud secrets, calendars, event cache, reminder history, RIC links. You can `/register` again later.

## Commands

**Everyone (menu depends on status)**

| Command | Who | What |
| --- | --- | --- |
| `/start`, `/help` | All | Status-aware menu with buttons |
| `/register` | All | Sign-up conversation |
| `/status` | Registered | Account summary |
| `/cancel` | During `/register` | Abort sign-up |
| `/delete` | Registered | Erase all stored data |

**Approved users**

| Command | What |
| --- | --- |
| `/calendars` | Enable/disable calendars |
| `/reminders` | Lead time and repeat count |
| `/txgroup [groups]` | Transmitter groups |
| `/server [es\|de]` | DAPNET core |
| `/rics [add\|remove] …` | Destination RICs |
| `/timezone Zone/Name` | Timezone |
| `/test` | Test DAPNET page |
| `/refresh` | Reload upcoming events |

**Admins only** (hidden from other users’ BotFather menu and `/help`; unknown-command if a non-admin types them)

| Command | What |
| --- | --- |
| `/pending` | Waiting registrations |
| `/users` | Registered users |
| `/approve <telegram_id>` | Approve |
| `/reject <telegram_id>` | Reject |

`/rics` shortcuts:

- `/rics` — menu
- `/rics 145904` — add if the RIC is already known
- `/rics 145904 ea4hqf` — add a new RIC with its owner callsign
- `/rics remove 145904`

## Reminders

Lead choices: **15 min, 30 min, 1 hour, 3 hours, 1 day, 1 week**. Repeats: **1, 2, or 3**, spaced evenly from the lead time down, **plus T-0 at event start**.

Examples:

- 60 min × 1 → T-60 and **at event time**
- 60 min × 3 → T-60, T-40, T-20, and **at event time**

All-day events are treated as **09:00** in the user’s timezone (T-0 is 09:00, not midnight).

Each due offset sends:

1. DAPNET page: `CALLSIGN: summary dd/mm[ HH:MM]` (all-day omits the clock), max 80 characters, accents/`¿¡` stripped.
2. Telegram: longer text (title, when, where, timezone, DAPNET result). Header is “Upcoming event in …” or **“Event starting now”** at T-0.

If DAPNET fails but Telegram succeeds, that offset is marked sent (no DAPNET retry). If both fail, the next dispatch cycle retries while the reminder is still within `MISFIRE_GRACE_MINUTES` (default 30).

There is no JobQueue persistence. After a restart, the grace window avoids flooding old due times.

## Calendar sync

- **Automatic:** every `SYNC_INTERVAL_SECONDS` (default 10 minutes), first run ~10 seconds after start. Approved users, enabled calendars only. Window: now − 1 hour through `FETCH_EVENT_WINDOW_DAYS` (14).
- **Manual:** `/refresh`, Help → Refresh events, or Calendars → Refresh events.

CalDAV `search(..., event=True, expand=True)`. `STATUS:CANCELLED` is ignored. Recurring instances are one cache row each. Turning a calendar **OFF** deletes its cached events.

This is **poll**, not CalDAV webhooks. If CalDAV auth fails, the user gets a Telegram error (not a pager).

## DAPNET

Production **API 1.1** (`/calls`, `/users`, `/callSigns`). Do not use API 2.0.

```json
{
  "text": "EA1XXX: Meeting 07/09 18:00",
  "callSignNames": ["ea1xxx", "ea4hqf"],
  "transmitterGroupNames": ["all", "ea-all"],
  "emergency": false
}
```

`callSignNames` are the **enabled RIC owner callsigns**. Duplicate callsigns are sent once. If the user has no RIC rows yet, the page goes to their DAPNET callsign. If they have RICs but all are OFF, nothing is sent until they enable one.

An invalid transmitter group name can cause DAPNET to drop the **whole** call. An empty group list is stored as `all`.

The `pagers` array on `GET /callSigns/{cs}` is often hidden for non-admin operators. Then existence of the callsign is enough at register time; RadioID and the user’s RIC list are the practical pager identity.

DMR IDs above 2097151 have the first digit stripped so they fit the POCSAG RIC range (same rule as PagerBot). RadioID network errors do not block registration.

## Data and security

- SQLite + SQLAlchemy async (`aiosqlite`). No Alembic; new `users` columns are added in `db/session.py` (`dapnet_rics`, `dapnet_server`). New tables (`rics`, `user_rics`) are created with `create_all`. Old `users.dapnet_rics` CSV values are backfilled into `user_rics` on startup.
- Nextcloud app passwords: Fernet (`ENCRYPTION_KEY`).
- Do not log app passwords or `DAPNET_PASSWORD`.
- Do not commit `.env`, `data/`, or `*.db`.
- Telegram messages never use Markdown (PagerBot had too many parse failures).
- `/delete` removes the user’s calendars, events, sent-reminder rows, RIC links, and encrypted Nextcloud secret. The shared RIC catalog (`rics`) stays so other users can still resolve that RIC.

There is no automatic database backup. Copy `data/bot.db` yourself.

## Project layout

```
src/telegram_dapnet_bot/
  main.py              # Application, jobs
  config.py            # pydantic-settings
  crypto.py            # Fernet
  bot/                 # Telegram handlers
  db/                  # models, repo, SQLite
  services/            # DAPNET, CalDAV, RadioID, reminders
tests/                 # unit tests (pytest)
PagerBot/              # REFERENCE. Not the product.
```

Run tests:

```bash
pip install -e ".[dev]"
pytest
```

## Known limitations

- No `/send`, broadcast, or POCSAG listener.
- No configurable page templates.
- You cannot pick a single RIC when several pagers share one DAPNET callsign: API 1.1 pages **all** pagers of that callsign.
- No extra “Telegram only” channel separate from DAPNET timing; both fire on the same offsets.
- SQLite only (no Postgres). No CalDAV push. No Alembic.
- Recurrence expansion depends on python-caldav 3.x `search(..., expand=True)`.

## License

[GPL-3.0-or-later](LICENSE)
