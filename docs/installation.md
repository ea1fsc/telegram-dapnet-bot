# Installation

You can run the bot with a Python virtual environment or with Docker. Both need a filled-in `.env` file (see [Configuration](configuration.md)).

**Requirements**

- Python **3.12 or newer**, or Docker Engine + Docker Compose
- Network access to Telegram, your users’ Nextcloud instances, DAPNET, and (optional) RadioID
- Disk space for `data/bot.db` (small; a few megabytes is typical)

The Telegram UI and this documentation assume a **private chat** with the bot, not a group.

## 1. Get the source

```bash
git clone https://github.com/YOUR-ORG/telegram-dapnet-bot.git
cd telegram-dapnet-bot
```

If you already have a copy, `cd` into that directory instead.

## 2. Create `.env`

```bash
cp .env.example .env
```

Never commit `.env`. It holds tokens and passwords. Generate `ENCRYPTION_KEY` **before** the first start:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

If Python is not installed yet, generate the key after you create the virtualenv (step 3), or run the same one-liner inside the Docker image later. Paste the result into `ENCRYPTION_KEY` with no quotes.

Fill the other required variables. Details: [Configuration](configuration.md). How to obtain a bot token and your Telegram id: [Operator guide](operator.md).

## Option A — Python virtualenv

### Create the environment

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

`python` must be 3.12+. On some systems the binary is `python3`.

`".[dev]"` installs the bot **and** pytest. For a production host you can use:

```bash
pip install -e .
```

### Run

```bash
python -m telegram_dapnet_bot
```

Equivalent:

```bash
telegram-dapnet-bot
```

On first start the process creates `./data/bot.db` (or whatever `DATABASE_URL` points to). Leave the terminal open. Use a process manager (systemd, OpenRC, `tmux`) if you want it to survive logout — see [Operator guide](operator.md).

Talk to the bot in Telegram. `/start` and `/help` show a command menu with buttons.

### Tests (optional)

```bash
pip install -e ".[dev]"
pytest
```

## Option B — Docker Compose

```bash
cp .env.example .env
# edit .env — same variables as Option A
docker compose up --build -d
```

What this does:

- Builds an image from `python:3.12-slim`
- Starts `python -m telegram_dapnet_bot`
- Mounts `./data` on the host to `/app/data` in the container so SQLite survives rebuilds
- Mounts `./certs` read-only at `/app/certs` (public Cloudflare Origin CA roots)
- Restarts the container unless you stop it (`restart: unless-stopped`)

Useful commands:

```bash
docker compose logs -f bot    # follow logs
docker compose ps             # status
docker compose down           # stop
docker compose up --build -d  # rebuild after a git pull
```

`DATABASE_URL` in `.env.example` is `sqlite+aiosqlite:///./data/bot.db`. Inside the container the working directory is `/app`, so the file appears on the host as `./data/bot.db`. Keep that path; do not point it at a location outside `/app/data` or the volume will not contain the database.

If Nextcloud sits behind a Cloudflare tunnel and Nginx Proxy Manager uses a **Cloudflare Origin CA** certificate, the bot may see that origin cert instead of Cloudflare’s public edge certificate. Set `CALDAV_CA_BUNDLE=/app/certs/cloudflare-origin-ca.pem` (venv: `./certs/cloudflare-origin-ca.pem`). Leave it unset when Nextcloud uses Let’s Encrypt or another public CA. See [CalDAV TLS](configuration.md#caldav-tls).

## After it is running

1. Open Telegram, search for your bot, tap **Start**.
2. You should see the help text. If you are listed in `ADMIN_TELEGRAM_IDS`, admin commands appear at the bottom.
3. Register a test account with `/register`, then approve it (see [Administrator guide](administrator.md)).
4. Send `/test` after approval. Your pager (and the Telegram chat) should get a short page.

If nothing happens, go to [Troubleshooting](troubleshooting.md).

## Upgrading

```bash
git pull
# Python:
source .venv/bin/activate
pip install -e .
# Docker:
docker compose up --build -d
```

There is no Alembic. On startup the bot runs `create_all`, adds missing `users` columns (`dapnet_rics`, `dapnet_server`), and backfills old CSV RIC values into `user_rics`. Keep a copy of `data/bot.db` before you upgrade. See [Security and privacy](security.md).

## Uninstall

Stop the process or run `docker compose down`. Delete the clone. Optionally delete `data/bot.db` — that erases every registered user. Telegram does not automatically delete the bot; revoke the token in BotFather if you are done with it.
