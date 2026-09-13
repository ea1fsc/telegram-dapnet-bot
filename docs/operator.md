# Operator guide

This page is for the person who **hosts** the bot: creating the Telegram bot, putting secrets in `.env`, keeping the process alive, and backing up data. Approving users is covered in the [Administrator guide](administrator.md) (often the same person).

## 1. Create the Telegram bot

1. Open Telegram and talk to [@BotFather](https://t.me/BotFather).
2. Send `/newbot` and follow the prompts (display name, then `@username` ending in `bot`).
3. Copy the **token**. Put it in `TELEGRAM_BOT_TOKEN`.
4. Optional: `/setprivacy` — for a private-chat bot the default is fine.
5. Optional: `/setdescription` so people know this is a DAPNET calendar reminder bot.

You do **not** need to register commands in BotFather. On startup the process sets a default command menu for everyone, and a longer menu (with `/pending`, `/users`, `/approve`, `/reject`) only for chats in `ADMIN_TELEGRAM_IDS`.

If BotFather still shows an old list, the bot may not have started successfully, or the admin id is wrong so the extra commands never attach to your chat.

## 2. Find your numeric Telegram id

The bot does not treat `@username` as an admin. You need the number.

1. Message [@userinfobot](https://t.me/userinfobot) (or any similar id bot).
2. Copy the id, for example `123456789`.
3. Put it in `ADMIN_TELEGRAM_IDS`. Several admins: `111,222,333`.

Then **open your own bot and tap Start**. Until you do that, Telegram cannot deliver “New registration request” messages to you.

## 3. DAPNET operator account

Pages are always sent with HTTP Basic auth using `DAPNET_CALLSIGN` and `DAPNET_PASSWORD`. That account must be allowed to `POST /calls` on the cores you configured.

Checklist:

- You can log in at [hampager.de](https://hampager.de/) and/or the Spanish core.
- The password in `.env` is the DAPNET password, not a Telegram or Nextcloud password.
- You are using **API 1.1** base URLs (`https://hampager.de/api`, `http://dapnet.es:8080`), not API 2.0.

The page **text** starts with the **end user’s** callsign (`EA1XXX: Meeting 07/09 18:00`). Recipients in `callSignNames` are the enabled RIC owner callsigns. Duplicate callsigns are sent once.

If the operator account cannot see the `pagers` array on `GET /callSigns/{cs}` (common for non-admin operators), registration still succeeds when the user and subscriber exist. RadioID and manual RIC entry are then the practical way to identify pagers.

## 4. Encryption key

Generate once:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Store `ENCRYPTION_KEY` next to backups of `data/bot.db`. Losing either piece makes Nextcloud passwords unrestorable.

## 5. Run it as a service

### Docker (simplest on a VPS)

Follow [Installation](installation.md) Option B. `restart: unless-stopped` brings the container back after a reboot.

### systemd (Python venv)

Example unit (adjust paths and the user):

```ini
[Unit]
Description=telegram-dapnet-bot
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=dapnet
WorkingDirectory=/home/dapnet/telegram-dapnet-bot
Environment=PATH=/home/dapnet/telegram-dapnet-bot/.venv/bin
ExecStart=/home/dapnet/telegram-dapnet-bot/.venv/bin/python -m telegram_dapnet_bot
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

The process uses **long polling** (`allowed_updates`: `message`, `callback_query`). You do not need a public HTTPS URL or webhook.

## 6. What “healthy” looks like

Logs at `INFO` include:

- application start (python-telegram-bot / httpx noise is reduced);
- `DAPNET POST /calls …` when a reminder or `/test` fires;
- `Reminded CALLSIGN for … offset=… dapnet=… telegram=…`.

In Telegram:

- `/start` replies with help and buttons;
- admins see Pending / Users on that help screen;
- `/pending` replies `There are no pending requests.` when the queue is empty (not “unknown command”).

The bot only accepts **private** command traffic as implemented; do not expect group-chat workflows.

## 7. Backups

There is **no** automatic backup. Copy these together:

| Item | Why |
| --- | --- |
| `data/bot.db` | Users, calendars, event cache, sent reminders, RIC catalog |
| `.env` (especially `ENCRYPTION_KEY`) | Without the key, app passwords in the DB are useless |

SQLite: stop the bot or copy a consistent snapshot (`sqlite3 data/bot.db ".backup backup.db"`). Keep the backup off the same disk.

Restoring: stop the bot, replace `data/bot.db`, restore the matching `.env`, start again.

## 8. Logs and disk

SQLite grows with events and `sent_reminders`. Turning a calendar **OFF** deletes its cached events. `/delete` removes one user’s row and related data; the shared `rics` catalog stays.

Rotate your own logs if you redirect stdout to a file. Docker: `docker compose logs --since 24h bot`.

## 9. Multiple admins

List every id in `ADMIN_TELEGRAM_IDS`. Each admin gets:

- the Approve / Reject notice on new registrations;
- `/pending`, `/users`, `/approve`, `/reject`;
- admin buttons on `/help`;
- a BotFather-style command menu scoped to **their** chat.

Non-admins who type `/approve` receive the same “I do not know that command” text as a typo. Do not treat that as a leak of admin features.

## 10. What you are responsible for

- Keeping the host online during the event window you care about (`MISFIRE_GRACE_MINUTES` is only 30 minutes by default).
- Not publishing `.env` or `data/`.
- Telling users the bot `@username`, that they need a DAPNET subscriber, and that they must use a Nextcloud **app password**.
- Approving only people you trust: their calendars are fetched with credentials stored on **your** server.
