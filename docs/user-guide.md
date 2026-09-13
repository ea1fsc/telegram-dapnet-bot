# User guide

This guide is for radio amateurs who want calendar events on their DAPNET pager (and a copy in Telegram). You do **not** install Python. You only need Telegram, a DAPNET account, and Nextcloud.

The bot’s messages are English and never use Markdown. You can tap buttons or type the same commands.

## What you need

1. The bot’s Telegram username (ask the person who runs it).
2. A **DAPNET** login whose callsign exists **and** has a subscriber (at least one RIC / pager). Create or check this on [hampager.de](https://hampager.de/) (and the Spanish core if that is where you operate).
3. A **Nextcloud** (or compatible CalDAV) account.
4. A Nextcloud **app password**, not your login password if two-factor authentication is on:
   - Nextcloud → **Settings** → **Security**
   - Create a new app password
   - Copy it once; you will paste it into the bot

## 1. Open the bot

In Telegram, open the bot and send `/start` (or tap **Start**). You will see a short explanation and **Register** / **Status** buttons.

Until you register, `/calendars` and similar commands reply that you are not registered.

## 2. Register (`/register`)

Send `/register` or tap **Register**. You have **600 seconds** (10 minutes) for the whole conversation. `/cancel` aborts.

### Callsign

Send your DAPNET callsign (letters and numbers, 3–20 characters; `/` is allowed). The bot checks DAPNET.

Typical errors:

- not a registered DAPNET user;
- no subscriber / no RIC — add a pager on hampager.de and try again;
- DAPNET unreachable — wait and retry.

Callsign lookup uses the **operator’s default core** (usually Germany). If your callsign exists only on the other core, ask the operator or see [FAQ](faq.md).

### Core (where pages are sent)

Tap **Spain (dapnet.es)** or **Germany (hampager.de)**. This is the network that will **transmit** your reminders. You can change it later with `/server`.

### RICs (which pagers get pages)

The bot lists suggestions:

- **RadioID** DMR IDs mapped into the POCSAG RIC range (ON by default if found);
- visible DAPNET pagers, if the operator account can see them.

You can:

- tap a row to toggle **ON** / **OFF**;
- tap **Enter RIC manually** and send a number (1–2097151);
- type a RIC number in the chat.

If that RIC is already in this bot’s catalog, its callsign is reused. If it is new, send the DAPNET callsign that **owns** the pager, or tap **Use my callsign**.

Tap **Done** when **at least one** RIC is selected.

**Important:** DAPNET delivers a page to **every pager of that callsign**. You cannot target a single RIC when several pagers share one callsign. See [Limitations](limitations.md).

### Nextcloud

1. **URL** — any instance. Examples: `https://cloud.example.org` or a full CalDAV URL. The bot adds `https://` and `/remote.php/dav` if missing. Only `http` / `https` (no `file:`).
2. **Username** — your Nextcloud login name.
3. **App password** — paste it. The bot tries to **delete** that message from the chat so it does not stay on screen. If deletion fails (Telegram privacy settings), delete it yourself.

The bot immediately tries to list calendars. If the URL, user, or password is wrong, it asks you to send another URL (or `/cancel`). TLS failures (`CERTIFICATE_VERIFY_FAILED`) are an **operator** problem on the bot host (Origin CA / proxy), not a bad app password. Ask the operator; see [Troubleshooting](troubleshooting.md).

### After submit

You should see: registration submitted, wait for an administrator. Check `/status`.

If you were **already approved** and you registered again with the **same** callsign, you stay approved and credentials are updated. If you **changed** callsign, you go back to pending.

## 3. Wait for approval

An admin must approve you. You cannot speed this up from the bot.

While **pending** you can use `/status`, `/register` (new details), `/delete`, `/cancel` (if a conversation is still open), `/help`.

If you are **rejected**, `/register` again after you have sorted it out with the admin.

## 4. After you are approved

Open `/help`. You should see calendars, reminders, TX groups, DAPNET core, RICs, timezone, test page, refresh, delete.

### Turn calendars ON (`/calendars`)

**ON** = that calendar is synced and reminded. **OFF** = ignored (cached events for that calendar are deleted).

New calendars start **OFF**. Nothing is paged until you enable at least one.

- **Refresh list** — re-read calendar names from Nextcloud (new calendars appear here).
- **Refresh events** — pull upcoming events now (same as `/refresh`) and list them.

If the list is empty, tap refresh or run `/register` again with a working app password.

### Reminder timing (`/reminders`)

Choose **lead time** and how many alerts **before** the event. The bot **always** also pages **at event start**.

Lead choices: 15 min, 30 min, 1 hour, 3 hours, 1 day, 1 week.  
Repeats: 1×, 2×, or 3×, spaced evenly from the lead time down, **plus T-0**.

Examples:

- 60 min × 1 → T-60 and **at event time**
- 60 min × 3 → T-60, T-40, T-20, and **at event time**

All-day events are treated as **09:00** in your timezone (T-0 is 09:00, not midnight).

Each due time sends:

1. DAPNET page: `CALLSIGN: summary dd/mm[ HH:MM]` (all-day omits the clock), max 80 characters, accents and `¿¡` stripped.
2. Telegram: title, when, where, timezone, and whether DAPNET succeeded. Header is “Upcoming event in …” or **“Event starting now”**.

### Timezone (`/timezone`)

```
/timezone Europe/Madrid
```

Use an [IANA name](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones). Without an argument, the bot shows the current value.

### Transmitter groups (`/txgroup`)

Which DAPNET transmitters radiate the page. Presets: `all`, `ea-all`, `dl-all`, `us-all`. Tap ON/OFF or send:

```
/txgroup ea-all,dl-all
```

**Refresh DAPNET groups** loads extra names from the core you selected. An invalid group name can make DAPNET drop the **entire** call. Leave `all` if you are unsure.

### DAPNET core (`/server`)

Spain or Germany for **sending**. Same as during registration. Shortcuts: `/server es`, `/server de` (aliases: `ea`, `spain`, `1`).

### Destination RICs (`/rics`)

Add, enable, disable, or remove pagers.

- `/rics` — menu
- `/rics 145904` — add if the RIC is already known to this bot
- `/rics 145904 ea4hqf` — add a new RIC with owner callsign
- `/rics remove 145904`

If you have **no** RIC rows, pages go to your DAPNET callsign. If you have RICs but **all are OFF**, DAPNET is not sent until you enable one (you may still get the Telegram reminder saying the page could not be sent).

### Test (`/test`)

Sends a short page: `YOURCALL: test telegram-dapnet-bot` to the enabled RIC callsigns. Use this after approval, after changing core/groups/RICs, and when a pager is silent.

### Refresh (`/refresh`)

Pulls events from enabled calendars for the next 14 days (operator can change that window) and lists up to 15 upcoming items. The automatic poll (default every 10 minutes) does the same in the background. This is **polling**, not instant push: a brand-new event can take until the next sync.

Cancelled events (`STATUS:CANCELLED`) are ignored. Recurring meetings become one reminder series per instance.

## 5. Check your account (`/status`)

Shows approval state, callsign, RICs, Nextcloud URL, timezone, reminder lead × repeats, TX groups, and core.

## 6. Leave (`/delete`)

Erases your row: Nextcloud secrets, calendars, event cache, reminder history, RIC links, callsign and preferences. The shared RIC catalog stays so other users can still resolve that number.

Confirm with the buttons or `/delete confirm`. You can `/register` again later.

## Quick path after approval

1. `/calendars` — turn the right calendars **ON**.
2. `/timezone Your/Zone`
3. `/reminders` — pick lead time.
4. `/rics` — confirm destinations.
5. `/test` — confirm the pager beeps.
6. `/refresh` — confirm events appear.

If something fails, see [Troubleshooting](troubleshooting.md) and [FAQ](faq.md).
