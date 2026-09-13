# Getting started

This bot sits between three systems you already (or will) use:

1. **Telegram** — where people talk to the bot.
2. **Nextcloud** (or any compatible CalDAV server) — where each user’s calendars live.
3. **DAPNET** — the amateur-radio paging network that delivers short text to POCSAG pagers.

An administrator must approve every registration. After that, a background job polls calendars and another job sends due reminders as:

- a DAPNET page (max 80 characters, sanitised), and
- a Telegram message with the same event.

Auth for DAPNET is always the **operator** credentials in `.env`. The page goes to the **callsigns of the user’s enabled RICs**. DAPNET API 1.1 has no “send to this RIC number” field.

```
Telegram user  →  Nextcloud CalDAV (their instance)
                     ↓ poll every 10 min (default)
                 event cache (SQLite)
                     ↓ every 60 s (default)
         DAPNET page + Telegram reminder
```

## Who should use this

Use this project if you:

- run (or will run) a small Telegram bot for a club, a family of hams, or yourself;
- want calendar events to show up on DAPNET pagers without typing each page by hand;
- are willing to approve each person who registers.

Do **not** expect a public paging gateway, a `/send` command, a POCSAG listener, or a multi-language UI. See [Limitations](limitations.md).

## What you need before anything else

**If you are the operator (you run the software)**

- A computer or VPS that can stay online (Linux is the usual choice).
- [Python 3.12+](https://www.python.org/downloads/) **or** [Docker](https://docs.docker.com/get-docker/).
- A Telegram account, so you can create a bot with [@BotFather](https://t.me/BotFather).
- Your numeric Telegram user id (for example from [@userinfobot](https://t.me/userinfobot)).
- A DAPNET operator account (callsign + password) that can `POST /calls`.

**If you are an end user**

- A DAPNET user whose callsign exists and has a subscriber (RIC).
- Nextcloud (or compatible CalDAV) with an **app password**.  
  Nextcloud → Settings → Security. Do not use the main password if two-factor authentication is on.
- The Telegram bot username that your operator published.

## Typical first-week flow

1. Operator follows [Installation](installation.md) and [Configuration](configuration.md).
2. Operator (as admin) opens the bot in Telegram so they can receive registration notices. See [Operator guide](operator.md).
3. A ham sends `/register`. See [User guide](user-guide.md).
4. Admin taps **Approve**. See [Administrator guide](administrator.md).
5. The user turns calendars **ON**, sets timezone and reminder lead time, and optionally sends `/test`.
6. When an event is due, the pager and Telegram both fire.

## Next step

- New to the vocabulary? Read the [glossary](glossary.md).
- Ready to run the code? Go to [installation](installation.md).
- Already have a running bot? Jump to the [user guide](user-guide.md) or [administrator guide](administrator.md).
