# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project uses [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Optional CalDAV TLS settings `CALDAV_SSL_VERIFY` and `CALDAV_CA_BUNDLE`. When unset, verification is unchanged (`true`, public CA store only).
- Bundled **public** Cloudflare Origin CA roots (RSA + ECC) at `certs/cloudflare-origin-ca.pem` ([Cloudflare Origin CA](https://developers.cloudflare.com/ssl/origin-configuration/origin-ca/)). No private keys. `CALDAV_CA_BUNDLE` merges that file with the public store so Cloudflare edge and an origin proxy (e.g. Nginx Proxy Manager) both verify.
- On CalDAV TLS failure, log resolved IPs and the peer certificate subject/issuer (`CalDAV TLS peer for …`).

### Changed

- CalDAV TLS errors in Telegram now mention `CALDAV_CA_BUNDLE` instead of dumping the raw `HTTPSConnectionPool` traceback.

## [0.1.0] - 2026-09-13

First release of **telegram-dapnet-bot**: a Telegram bot that syncs per-user Nextcloud CalDAV calendars and sends DAPNET pages (API 1.1) plus Telegram reminders.

### Added

#### Platform

- Python 3.12+ package `telegram_dapnet_bot` (`src/` layout), GPL-3.0-or-later.
- `pyproject.toml`, Docker image, `docker-compose.yml`, `.env.example`.
- SQLite persistence via SQLAlchemy async / aiosqlite (`DATABASE_URL`).
- Fernet encryption for Nextcloud app passwords (`ENCRYPTION_KEY`).
- Logging; JobQueue for CalDAV sync and reminder dispatch.
- Lightweight schema updates: `create_all`, `ALTER` for `users.dapnet_rics` and `users.dapnet_server`, backfill of CSV RICs into `user_rics`.

#### Registration and access

- `/register` conversation (600 s timeout): callsign, DAPNET core, RICs, Nextcloud URL / user / app password.
- Callsign validation against DAPNET `GET /users/{cs}` and `GET /callSigns/{cs}` (also `/callsigns`).
- RadioID DMR lookup; IDs above 2097151 mapped into the POCSAG RIC range.
- Admin approval: `/pending`, `/users`, `/approve <id>`, `/reject <id>`, and Approve/Reject buttons.
- Re-register: same callsign stays approved; a new callsign goes pending again.
- `/status`, `/cancel`, `/delete` (confirmation buttons or `/delete confirm`).
- `require_approved` gate for calendar/reminder/send commands.

#### Destination RICs

- Shared catalog table `rics` and per-user `user_rics` (enable/disable, owner callsign, source).
- During register: RadioID matches, visible DAPNET pagers, manual RIC, reuse of catalog callsigns, “use my callsign”.
- `/rics` after approval: buttons and commands (`/rics 145904`, `/rics 145904 CALLSIGN`, `/rics remove 145904`).
- Pages sent with `callSignNames` = unique enabled RIC owner callsigns (API 1.1). Fallback to the user’s callsign if they have no RIC rows.

#### Calendars and reminders

- `/calendars`: enable/disable, refresh CalDAV list, refresh upcoming events.
- `/refresh`: same event reload as the calendars button; lists the fetch window.
- `/reminders`: lead 15 / 30 / 60 / 180 / 1440 / 10080 minutes; 1–3 equally spaced alerts **plus T-0 at event start**.
- All-day events treated as 09:00 in the user’s timezone.
- Automatic CalDAV poll (`SYNC_INTERVAL_SECONDS`, default 600 s) for approved users with enabled calendars; window now−1 h … `FETCH_EVENT_WINDOW_DAYS` (14). `expand=True`; cancelled events ignored.
- Dispatch job (`DISPATCH_INTERVAL_SECONDS`, default 60 s): DAPNET `POST /calls` and a Telegram reminder; misfire grace `MISFIRE_GRACE_MINUTES` (30).
- Sent-reminder unique key per user / uid / recurrence / offset.

#### DAPNET send options

- `/txgroup`: multiple transmitter groups (CSV), presets `all`, `ea-all`, `dl-all`, `us-all`, refresh from `GET /transmitterGroups`.
- `/server`: Spain (`dapnet.es`) or Germany (`hampager.de`); aliases `es`/`de`/`ea`/`1`.
- `/timezone`, `/test`.
- Page text: `{CALLSIGN}: {sanitised summary} {dd/mm[ HH:MM]}`, max 80 characters, sanitised for POCSAG.
- HTTP retries on 429 / 5xx. Operator Basic auth. No DAPNET API 2.0.

#### Telegram UI

- English-only user/admin messages; **no Markdown**.
- `/start` and `/help` with buttons that match registration status (not registered / pending / rejected / approved).
- Admin commands listed in `/help` and BotFather **only** for `ADMIN_TELEGRAM_IDS` chats; other users get the unknown-command reply.
- Buttons and chat commands for the same actions where it matters (`/help`, `/delete`, `/refresh`, `/rics`, `/txgroup`, `/server`, calendars, reminders).

#### Tests

- Unit tests for format, offsets (including T-0), crypto, DB, DAPNET subscriber/pagers, RadioID, TX groups, help menus, RIC destinations.

### Notes

- Out of scope: `/send`, broadcast, POCSAG listeners, Postgres, i18n, CalDAV webhooks, Alembic, per-RIC send when several pagers share one callsign, configurable page templates.
