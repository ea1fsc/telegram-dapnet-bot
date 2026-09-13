# Configuration

All settings come from environment variables, usually via a `.env` file next to `docker-compose.yml`. Copy the template:

```bash
cp .env.example .env
```

The bot loads `.env` through pydantic-settings. Names are case-insensitive in code (`TELEGRAM_BOT_TOKEN` maps to `telegram_bot_token`). Extra unknown variables are ignored.

Never commit `.env`. `.gitignore` already excludes it.

## Required

| Variable | Meaning |
| --- | --- |
| `TELEGRAM_BOT_TOKEN` | Token from [@BotFather](https://t.me/BotFather). Format `123456:ABC-…`. |
| `ADMIN_TELEGRAM_IDS` | Comma-separated numeric Telegram user ids that can approve people. Example: `123456789` or `111,222`. Spaces around commas are fine. Usernames (`@alice`) are **not** accepted. |
| `DAPNET_CALLSIGN` | Operator callsign used as HTTP Basic user on every DAPNET request. |
| `DAPNET_PASSWORD` | Operator DAPNET password. |
| `ENCRYPTION_KEY` | Fernet key used to encrypt Nextcloud app passwords at rest. |

Generate `ENCRYPTION_KEY` once and keep it forever for that database:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

If you lose this key, existing Nextcloud passwords in SQLite cannot be decrypted. Users must `/register` again (same callsign stays approved). If you **rotate** the key without re-registering users, CalDAV sync will fail.

At least one id in `ADMIN_TELEGRAM_IDS` is required in practice: nobody can approve registrations otherwise. Each of those people must already have started a chat with the bot, or Telegram will refuse the “new registration” notice.

## DAPNET endpoints and defaults

| Variable | Default | Meaning |
| --- | --- | --- |
| `DAPNET_API_URL` | `https://hampager.de/api` | Germany core (API **1.1**). Trailing slashes are stripped. |
| `DAPNET_API_URL_ES` | `http://dapnet.es:8080` | Spain core. |
| `DAPNET_DEFAULT_TX_GROUP` | `all` | Initial transmitter group stored for new users. |
| `DAPNET_DEFAULT_SERVER` | `de` | Initial core for new users and for **callsign lookup during `/register`**. Values: `de` / `es` (aliases `ea`, `spain`, `1` also work). |

Do **not** point these URLs at DAPNET API 2.0. The bot speaks API 1.1 (`/calls`, `/users`, `/callSigns`).

Registration checks `GET /users/{cs}` and `GET /callSigns/{cs}` on the **default** server (`DAPNET_DEFAULT_SERVER`), not on the core the user just picked for sending. If a callsign exists only on the other core, registration can fail. See [Limitations](limitations.md).

## Database

| Variable | Default | Meaning |
| --- | --- | --- |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/bot.db` | SQLAlchemy async URL. SQLite only. |

The directory of the database file is created automatically. With Docker, keep the path under `./data` so it lands on the named bind mount.

There is no PostgreSQL dialect, connection pool tuning, or Alembic migration folder.

## Scheduler

| Variable | Default | Meaning |
| --- | --- | --- |
| `SYNC_INTERVAL_SECONDS` | `600` | How often to poll CalDAV for approved users with enabled calendars. First run ~10 seconds after start. |
| `DISPATCH_INTERVAL_SECONDS` | `60` | How often to look for due reminders. First run ~20 seconds after start. |
| `FETCH_EVENT_WINDOW_DAYS` | `14` | How far ahead (and 1 hour back) to fetch events. |
| `MISFIRE_GRACE_MINUTES` | `30` | After downtime, still send a reminder if it became due within this many minutes. Older due times are skipped (no flood). |

Shorter sync intervals mean fresher calendars and more load on Nextcloud. Shorter dispatch intervals mean reminders closer to the exact minute, at the cost of more DAPNET/Telegram traffic when many events are due.

JobQueue state lives in memory. A restart does not “remember” that a job already ran; uniqueness is the `sent_reminders` table plus the grace window.

## Defaults for new users

Applied on first `/register`. Re-registering **keeps** timezone, transmitter groups, lead time, and repeat count if the user already exists.

| Variable | Default | Meaning |
| --- | --- | --- |
| `DEFAULT_TIMEZONE` | `Europe/Madrid` | IANA timezone. Users change it with `/timezone Europe/Madrid`. |
| `DEFAULT_LEAD_MINUTES` | `60` | First reminder this many minutes before the event. Users pick from 15 / 30 / 60 / 180 / 1440 / 10080. |
| `DEFAULT_REPEAT_COUNT` | `1` | Number of equally spaced alerts **before** T-0 (1–3). T-0 is always added. |

## Logging

| Variable | Default | Meaning |
| --- | --- | --- |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR`, or `CRITICAL`. Invalid values fall back to `INFO`. |

`httpx` and `httpcore` are forced to `WARNING` so HTTP chatter does not drown the log. DAPNET `POST /calls` is logged at INFO (destinations and groups, not passwords). Do not log `.env` or app passwords yourself.

## Example `.env`

```env
TELEGRAM_BOT_TOKEN=123456:ABC-your-bot-token
ADMIN_TELEGRAM_IDS=123456789

DAPNET_API_URL=https://hampager.de/api
DAPNET_API_URL_ES=http://dapnet.es:8080
DAPNET_CALLSIGN=yourcall
DAPNET_PASSWORD=your-dapnet-password
DAPNET_DEFAULT_TX_GROUP=all
DAPNET_DEFAULT_SERVER=de

ENCRYPTION_KEY=paste-fernet-key-here

DATABASE_URL=sqlite+aiosqlite:///./data/bot.db

SYNC_INTERVAL_SECONDS=600
DISPATCH_INTERVAL_SECONDS=60
FETCH_EVENT_WINDOW_DAYS=14
MISFIRE_GRACE_MINUTES=30

DEFAULT_TIMEZONE=Europe/Madrid
DEFAULT_LEAD_MINUTES=60
DEFAULT_REPEAT_COUNT=1

LOG_LEVEL=INFO
```

After editing `.env`, restart the process (or `docker compose up -d` after a change; Compose recreates the container when env_file changes on some setups — if in doubt, `docker compose down && docker compose up -d`).

## What you cannot configure

There is no setting for:

- page text templates (format is fixed: `CALLSIGN: summary dd/mm[ HH:MM]`);
- Telegram webhooks (the bot **polls**);
- a second “Telegram only” reminder channel;
- language / i18n;
- which DAPNET core is used for **user lookup** separately from `DAPNET_DEFAULT_SERVER`.
