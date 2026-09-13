# FAQ

Short answers. Deeper detail lives in the linked pages.

## General

**What does this bot do?**  
It reads your Nextcloud calendars and, before each event, sends a short DAPNET page and a Telegram message. An admin must approve you first. [Getting started](getting-started.md)

**Do I need to be a radio amateur?**  
End users need a DAPNET callsign and a pager (RIC). The operator needs a DAPNET account that can send calls.

**Does it cost money?**  
The software is GPL-3.0-or-later. Telegram, Nextcloud, and DAPNET have their own terms. You provide the VPS.

**What language is the bot?**  
English only, plain text.

## Users

**Where do I get an app password?**  
Nextcloud → Settings → Security → app passwords. [User guide](user-guide.md)

**Why can’t I use `/calendars` yet?**  
You are not approved. Wait, or ask an admin. `/status` shows the state.

**I changed my Nextcloud password.**  
Create a new app password and `/register` again. Same DAPNET callsign keeps you approved.

**I changed callsign.**  
`/register` with the new callsign. You become **pending** again.

**Can I receive pages on a friend’s pager?**  
Add their RIC and the **callsign that owns that pager**. DAPNET will page **all** pagers of that callsign, not only one RIC. [Limitations](limitations.md)

**Why is the page missing accents?**  
POCSAG-friendly sanitising strips accents and some symbols, max 80 characters.

**When do all-day events page?**  
09:00 in your `/timezone`, plus whatever lead offsets you set.

**How fast do new calendar entries appear?**  
Up to `SYNC_INTERVAL_SECONDS` (default 10 minutes), or immediately if you `/refresh`.

**How do I leave?**  
`/delete` then confirm. [Security](security.md)

**Can I use Google Calendar / Outlook?**  
Only if you expose CalDAV the way Nextcloud does, or you sync those calendars **into** Nextcloud. There is no Google OAuth.

## Admins / operators

**How do I become admin?**  
Put your numeric Telegram id in `ADMIN_TELEGRAM_IDS` and restart. [Operator guide](operator.md)

**Can I approve myself?**  
Yes: `/approve` your own Telegram id, if you are in the admin list.

**Do users see admin commands?**  
No. They get the unknown-command reply.

**Must the bot stay online 24/7?**  
For reliable pages, yes. Downtime longer than `MISFIRE_GRACE_MINUTES` (30) skips those due times.

**Can I run two bots with one token?**  
No. Telegram allows one `getUpdates` client per token.

**Can I change the 80-character layout?**  
Not without changing the code. No template setting.

**Is there a web interface?**  
No. Telegram + `.env` + SQLite.

**How do I back up?**  
Copy `data/bot.db` and `.env` (especially `ENCRYPTION_KEY`) together.

## DAPNET

**Germany or Spain?**  
`/server` chooses where the **page is sent**. Registration **lookup** uses the operator default (usually Germany). [Configuration](configuration.md)

**What is a transmitter group?**  
A named set of DAPNET transmitters (`all`, `ea-all`, …). Wrong names can drop the call. [User guide](user-guide.md)

**Why `/test` works but calendar pages do not?**  
Calendars still OFF, no events in the fetch window, or reminder time not reached yet. `/refresh` and `/calendars`.

**CalDAV says `CERTIFICATE_VERIFY_FAILED` / self-signed certificate.**  
The bot is verifying TLS against public CAs. Cloudflare **edge** certificates are public; a **Cloudflare Origin CA** certificate on Nginx Proxy Manager is not. Set `CALDAV_CA_BUNDLE` to the bundled public Origin CA roots (`/app/certs/cloudflare-origin-ca.pem` in Docker). Unset, the bot behaves as before. [CalDAV TLS](configuration.md#caldav-tls), [Troubleshooting](troubleshooting.md).

**Is `certs/cloudflare-origin-ca.pem` a private certificate?**  
No. It is Cloudflare’s published Origin CA **roots** (RSA + ECC), the same files as [Origin CA](https://developers.cloudflare.com/ssl/origin-configuration/origin-ca/). There is no private key. They only let the bot **verify** origin certificates. Your NPM origin cert and its key stay on the proxy.

## Something else

See [Troubleshooting](troubleshooting.md) and [Limitations](limitations.md).
