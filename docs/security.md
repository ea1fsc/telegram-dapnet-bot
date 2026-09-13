# Security and privacy

This bot stores calendar credentials and amateur-radio identifiers on the **operator’s** machine. Treat the host like a small identity provider.

## What is stored

SQLite (default `data/bot.db`):

| Data | Encrypted at rest? |
| --- | --- |
| Telegram user id and optional `@username` | No |
| DAPNET callsign, RIC numbers, RIC owner callsigns, core, TX groups | No |
| Nextcloud URL and username | No |
| Nextcloud **app password** | **Yes** (Fernet, `ENCRYPTION_KEY`) |
| Calendar names and CalDAV URLs | No |
| Cached event summaries, locations, start times | No |
| Which reminder offsets were already sent | No |

The operator DAPNET password lives only in `.env`, not in SQLite.

`/delete` removes that user’s calendars, events, sent-reminder rows, RIC **links**, and the encrypted Nextcloud secret. The shared RIC catalog (`rics`) remains so other users can still resolve that RIC to a callsign.

## Encryption key

`ENCRYPTION_KEY` is a Fernet key. Generate it with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

- Keep it with backups of `bot.db`.
- If it is lost, stored app passwords cannot be decrypted; users must `/register` again.
- Do not commit `.env`. `.gitignore` excludes `.env`, `data/`, and `*.db`.

The bot does not log app passwords or `DAPNET_PASSWORD`. Do not raise `LOG_LEVEL=DEBUG` in a setup that might print full HTTP bodies to a shared log.

## Telegram

- UI is **plain text** (no Markdown) to avoid parse failures.
- During `/register` the bot tries to **delete** the message that contained the app password. Users should still delete it if it remains.
- The bot uses **long polling**, not a webhook. You do not expose an HTTP port for Telegram.
- Admin commands are hidden from non-admin command menus. Typing them yields the generic unknown-command reply.

Admins see Nextcloud **URL and username** on registration notices, not the password.

## DAPNET

Every page is sent as the **operator** account. Recipients are callsigns, not raw RIC numbers. Do not approve users you do not trust: they can cause pages to be sent (within DAPNET’s own limits) using your operator credentials.

`emergency` is always `false`. There is no broadcast or `/send`.

## Network

The process connects outbound to:

- Telegram API
- DAPNET cores you configured
- Each user’s Nextcloud / CalDAV URL
- RadioID (`https://radioid.net/…`) during RIC suggestions

It does not require inbound ports. CalDAV URLs are restricted to `http` and `https` (`file:` is rejected).

## Operator hygiene

- Run as an unprivileged user.
- Restrict filesystem permissions on `.env` and `data/`.
- Backup `bot.db` **and** `ENCRYPTION_KEY` together.
- There is no automatic backup and no built-in multi-user “admin web UI”.
- SQLite is not hardened for untrusted local users on the same host; protect the file.

## GDPR-style notes (informal)

If you run this for other people, tell them:

- you store their Telegram id, callsign, calendar URLs, event titles/locations, and an encrypted app password;
- reminders are sent to DAPNET (visible on the amateur paging network) and Telegram;
- they can erase bot-side data with `/delete`;
- DAPNET and Telegram have their own retention; this project cannot unsay a page already transmitted.

This is not legal advice.
