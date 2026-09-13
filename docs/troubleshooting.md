# Troubleshooting

Work top-down: process running → Telegram answers → DAPNET `/test` → calendars ON → events in `/refresh`.

## The process does not start

| Symptom | Likely cause | What to do |
| --- | --- | --- |
| Immediate exit, missing env | Empty `.env` or unset required vars | Copy `.env.example`, fill all [required](configuration.md) fields. |
| Error about Fernet / key | `ENCRYPTION_KEY` missing or not a valid Fernet key | Generate a new key with the Python one-liner in Configuration. If users already exist, a **new** key cannot decrypt old passwords. |
| `JobQueue is not available` | Installed `python-telegram-bot` without extra | `pip install -e .` from this repo (pulls `python-telegram-bot[job-queue]`). |
| Python version error | Older than 3.12 | Install 3.12+ or use Docker. |
| `Conflict: terminated by other getUpdates` | Two processes use the same `TELEGRAM_BOT_TOKEN` | Stop the other container/systemd unit/laptop running the same bot. |

Docker: `docker compose logs bot`. Python: watch the terminal.

## Telegram does not answer

1. Confirm the token with BotFather (`/token` on your bot).
2. Search the exact `@username` and tap **Start**.
3. The bot only handles `message` and `callback_query` updates.
4. If you changed the token, restart the process.

## “I do not know that command”

- Typo, or you used an **admin** command without being in `ADMIN_TELEGRAM_IDS`.
- Restart after editing admin ids.
- `/help` shows what **you** are allowed to see.

## Admin never gets registration notices

1. Your numeric id (not `@username`) is in `ADMIN_TELEGRAM_IDS`.
2. You already sent `/start` to the bot.
3. You did not block the bot.
4. The user’s `/register` actually finished (they got “Registration submitted”).

## Registration fails at callsign

- Callsign must match letters/numbers/`/`, length 3–20.
- DAPNET user must exist on the **default** core (`DAPNET_DEFAULT_SERVER`, usually Germany).
- A **subscriber** (RIC) must exist. Add a pager on hampager.de.
- If pagers are visible to the operator and the count is 0, add a RIC on DAPNET.
- Transient: “I could not query DAPNET right now.”

Spain-only callsigns: ask the operator to set `DAPNET_DEFAULT_SERVER=es` **or** create the subscriber on the Germany core too. See [Limitations](limitations.md).

## Registration fails at Nextcloud

The bot could not list calendars.

- Use an **app password** (Settings → Security), especially with 2FA.
- URL should be the Nextcloud origin (`https://cloud.example.org`). The bot appends `/remote.php/dav` if needed.
- Username is the Nextcloud login, not an email alias unless that **is** the login.
- TLS errors (`CERTIFICATE_VERIFY_FAILED`, “self-signed certificate”): see [CalDAV TLS verification failed](#caldav-tls-verification-failed).
- CalDAV-compatible servers other than Nextcloud may work but are not a separate product mode.

## Approved but nothing is paged

1. `/status` must say **approved**.
2. `/calendars` — at least one calendar **ON**. New calendars default to OFF.
3. `/refresh` — do events appear in the next 14 days?
4. `/rics` — at least one RIC **ON**, or no RIC rows (fallback = your callsign). All-OFF means DAPNET send is skipped.
5. `/test` — if this fails, calendars are not the problem (core, TX groups, operator password, or destinations).
6. `/timezone` — all-day events fire at 09:00 **that** zone.
7. `/reminders` — you may be waiting for T-60 while expecting an immediate page; use `/test`.
8. Transmitter groups: an invalid name can drop the **whole** DAPNET call. Try `all`.
9. Core: `/server` must be the network your pager actually listens to.

## `/test` rejected by DAPNET

The reply includes the HTTP status and a short body.

- Wrong `DAPNET_PASSWORD` or callsign in `.env` (operator credentials).
- Operator not allowed to `POST /calls`.
- Empty destinations (all RICs OFF).
- Bad transmitter group list.
- Wrong API URL (must be API 1.1, not 2.0).
- Spain vs Germany: try the other core.

## Telegram reminder arrived, pager did not

By design, if DAPNET fails and Telegram works, the offset is **not retried** on DAPNET. The Telegram text will say the page could not be sent. Fix DAPNET (`/test`, groups, core, destinations) before the next event.

## Pager got a page, but not for a new event

Sync is every 10 minutes by default. Use `/refresh`. Events outside `FETCH_EVENT_WINDOW_DAYS` (14) are not fetched.

Cancelled events are ignored. Calendar still **OFF**? Enable it.

## Bot was down; I got a storm of old pages / I got none

Default grace is **30 minutes**. Due times older than that are skipped. There is no catch-up of a full weekend outage. Lower/higher: `MISFIRE_GRACE_MINUTES`.

## “Could not decrypt stored secret”

`ENCRYPTION_KEY` does not match the key used when the user registered. Restore the old key or ask users to `/register` again (same callsign stays approved).

## CalDAV TLS verification failed

The handshake failed before HTTP. Rate limits (429) are not this error.

Python verifies against **public** CAs. That works for Let’s Encrypt and for Cloudflare’s **edge** certificate (Google Trust Services / similar). It fails when the bot talks to the **origin** (Nginx Proxy Manager, Nextcloud HTTPS) and the cert is Cloudflare Origin CA or a true self-signed leaf. OpenSSL often reports Origin CA as “self-signed certificate” because that root is self-signed.

Typical homelab: Internet → Cloudflare tunnel → NPM (Origin CA) → Nextcloud. Browsers see the edge cert. A Docker bot on the same host as NPM often hairpins to NPM and sees Origin CA.

1. In the process log, find `CalDAV TLS peer for …`.
2. Issuer `Google Trust Services` / `WE1` and Cloudflare anycast IPs (`188.114…`, `104.…`) → you are on the edge; the bundle should not be required.
3. Issuer `CloudFlare Origin SSL` or a private IP → origin proxy. Set `CALDAV_CA_BUNDLE=/app/certs/cloudflare-origin-ca.pem` (venv: `./certs/cloudflare-origin-ca.pem`) and rebuild/restart. That file is Cloudflare’s **public** Origin CA roots, not a private key. [CalDAV TLS](configuration.md#caldav-tls).
4. Do not set `CALDAV_SSL_VERIFY=false` unless you accept man-in-the-middle risk on every user’s CalDAV URL.

Leaving both TLS variables unset is the old behaviour (public CAs only).

## CalDAV error messages in Telegram

Background sync could not read Nextcloud. App password rotated? URL changed? User should `/register` with new credentials.

If the message mentions TLS / Origin CA, it is an operator setting on the bot host, not a wrong app password. See the section above.

## Docker database disappeared

`DATABASE_URL` must stay under `./data` so the bind mount `./data:/app/data` holds `bot.db`. A path like `/tmp/bot.db` dies with the container.

## `/users` is incomplete

The command lists at most 50 rows. Query SQLite as operator if you have more.

## Tests fail on a clean clone

```bash
pip install -e ".[dev]"
pytest
```

Need Python 3.12+ and network-free unit tests (they should not call live DAPNET).
