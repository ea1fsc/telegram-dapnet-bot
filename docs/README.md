# Documentation

**telegram-dapnet-bot** is a Telegram bot that reads each user’s Nextcloud calendars and sends reminder pages on [DAPNET](https://hampager.de/). Pages are sent with **your operator account**. Recipients are the DAPNET callsigns behind the RICs each user selected.

Package version **0.1.0**. License **[GPL-3.0-or-later](../LICENSE)**. The Telegram UI is English, plain text (no Markdown).

If you have never used Telegram bots, Nextcloud, or amateur-radio paging, start with the glossary, then follow the path that matches your role.

## Choose your path

| I want to… | Read this |
| --- | --- |
| Understand what this project is | [Getting started](getting-started.md) |
| Learn the terms (DAPNET, RIC, CalDAV, …) | [Glossary](glossary.md) |
| Install and run the bot | [Installation](installation.md) |
| Fill in `.env` and tune intervals | [Configuration](configuration.md) |
| Host the bot (BotFather, backups, Docker) | [Operator guide](operator.md) |
| Approve or reject registrations | [Administrator guide](administrator.md) |
| Register and receive calendar pages | [User guide](user-guide.md) |
| Look up a command | [Command reference](commands.md) |
| Understand sync, reminders, and page text | [How it works](how-it-works.md) |
| Know what is stored and how to delete it | [Security and privacy](security.md) |
| See what the bot cannot do | [Limitations](limitations.md) |
| Fix a problem | [Troubleshooting](troubleshooting.md) |
| Find a short answer | [FAQ](faq.md) |

## Roles at a glance

- **Operator** — the person who clones the repository, creates the Telegram bot, puts DAPNET credentials in `.env`, and keeps the process running.
- **Administrator** — a Telegram user whose numeric id is listed in `ADMIN_TELEGRAM_IDS`. They approve registrations. Often the same person as the operator.
- **End user** — a radio amateur who registers a DAPNET callsign and a Nextcloud account so calendar events become pager messages.

You need at least one operator and one administrator. They can be the same person. End users never see `.env` or the server.

## Repository layout

```
telegram-dapnet-bot/
  docs/                      # This documentation
  src/telegram_dapnet_bot/   # The product
  tests/                     # pytest unit tests
  .env.example               # Template for secrets and settings
  docker-compose.yml
```
