# Glossary

Short definitions for people who have not used DAPNET, CalDAV, or Telegram bots before. Terms are listed in the order you are likely to meet them.

## Telegram

**Bot** — a program that talks in Telegram like a contact. You start a private chat with it and send commands such as `/start`.

**Bot token** — a secret string from [@BotFather](https://t.me/BotFather). It looks like `123456:ABC-…`. Anyone with the token can control the bot. Store it only in `.env`.

**Telegram user id** — a number that never changes, even if you rename your account. Admins are identified by this number, not by `@username`. [@userinfobot](https://t.me/userinfobot) prints yours.

**Command** — a message that starts with `/`, for example `/help`. The bot also offers buttons that do the same thing.

**Callback / inline button** — a button under a bot message. Tapping it does not send a visible chat message.

## Amateur radio paging

**DAPNET** — Decentralized Amateur Paging Network. Hams send short text pages to POCSAG pagers. Public cores include Germany ([hampager.de](https://hampager.de/)) and Spain ([dapnet.es](http://dapnet.es)).

**Core / server** — which DAPNET cluster **sends** the page. This bot supports Germany (`de`) and Spain (`es`). Choosing a core does not change where your callsign was registered; it changes which API receives `POST /calls`.

**Callsign** — your amateur-radio identifier, for example `EA1ABC`. In this bot it is 3–20 characters: letters, digits, and `/`.

**RIC** — Radio Identity Code, the numeric address of a pager (1–2097151). DAPNET API 1.1 does **not** accept “send to RIC 145904”. It accepts **callsigns**. The bot therefore stores “this RIC belongs to callsign X” and pages that callsign.

**Subscriber** — a DAPNET callsign that has at least one pager/RIC. Registration fails if the callsign has no subscriber.

**POCSAG** — the protocol pagers use. Pages are short; this bot caps text at **80 characters**.

**Transmitter group (spread)** — which DAPNET transmitters radiate the page, for example `all`, `ea-all`, `dl-all`, `us-all`. An invalid name can make DAPNET drop the **whole** call.

**Operator account** — the DAPNET login in `.env` (`DAPNET_CALLSIGN` / `DAPNET_PASSWORD`). Every page is authenticated as this account, even when the text starts with another user’s callsign.

**RadioID** — [radioid.net](https://radioid.net/) directory of DMR IDs. During registration the bot looks up the callsign and may suggest RICs. DMR IDs above 2097151 have the first digit stripped so they fit the POCSAG range.

## Calendars

**Nextcloud** — self-hosted file and calendar server. Any instance is fine; users do not have to share the operator’s Nextcloud.

**CalDAV** — the calendar protocol. Nextcloud exposes it at `/remote.php/dav`. Other CalDAV servers may work if they speak the same protocol.

**App password** — a long password Nextcloud generates for a single app (Settings → Security). Prefer this over the account password, especially with 2FA.

**Lead time** — how far **before** the event the first reminder fires (15 minutes up to 1 week).

**Repeat count** — how many equally spaced alerts fire **before** the event (1, 2, or 3). The bot **always** adds one more alert **at event time** (T-0).

**All-day event** — a calendar item with a date but no clock time. This bot treats it as **09:00** in the user’s timezone.

**IANA timezone** — a name such as `Europe/Madrid` or `America/New_York`. Used for all-day events and for “when” in reminders.

## This project

**Operator** — person who runs the Python/Docker process and owns `.env`.

**Administrator** — Telegram user listed in `ADMIN_TELEGRAM_IDS`. Approves registrations.

**Pending / approved / rejected** — the three registration states. Calendar commands work only when **approved**.

**Fernet** — the encryption used for Nextcloud app passwords at rest. The key is `ENCRYPTION_KEY`. If you lose it, stored passwords cannot be decrypted.

**SQLite** — the single-file database (`data/bot.db` by default). There is no PostgreSQL option.

**JobQueue** — in-memory scheduler from `python-telegram-bot`. Jobs are **not** persisted across restarts. A misfire grace window avoids flooding old reminders after downtime.
