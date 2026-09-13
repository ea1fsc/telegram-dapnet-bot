# Command reference

Commands work in a **private chat** with the bot. Buttons on `/help` and on each submenu call the same handlers. Messages never use Markdown.

`/help` shows only the commands that apply to your status. Admin commands appear only for chats listed in `ADMIN_TELEGRAM_IDS`.

## Everyone (menu depends on status)

| Command | Who can use it | What it does |
| --- | --- | --- |
| `/start` | All | Same as `/help`: status-aware text + buttons. |
| `/help` | All | Command menu. Footer: tap a button or type the command. |
| `/register` | All | Sign-up conversation (callsign, core, RICs, Nextcloud). Timeout **600 s**. |
| `/status` | Registered | Account summary. If you never registered: “You are not registered.” |
| `/cancel` | During `/register` or add-RIC conversation | Abort. |
| `/delete` | Registered | Confirmation. `/delete confirm` erases all stored data for you. |

Unknown `/commands` (including admin commands typed by non-admins):

```
I do not know that command. Use /help for the command menu.
```

## Approved users

These require status **approved**. Pending users are told to wait. Rejected users are told to `/register` again.

| Command | What it does |
| --- | --- |
| `/calendars` | Enable/disable calendars. Buttons: **Refresh list**, **Refresh events**. |
| `/reminders` | Lead time (15 min … 1 week) and repeat count (1–3). T-0 is always added. |
| `/txgroup` | Show transmitter-group buttons. |
| `/txgroup ea-all,dl-all` | Set groups (comma-separated or multiple arguments). Letters, digits, hyphens. Empty/invalid → error. Stored empty list becomes `all`. |
| `/server` | Show Spain / Germany buttons. |
| `/server es` or `/server de` | Set core. Aliases: `ea`, `spain`, `1` → Spain; anything else → Germany. |
| `/rics` | Destination RIC menu (toggle ON/OFF, Remove, Add RIC). |
| `/rics 145904` | Add a RIC already in the catalog. |
| `/rics 145904 ea4hqf` | Add a RIC with owner callsign. |
| `/rics add 145904` | Same as `/rics 145904`. |
| `/rics remove 145904` | Remove from **your** list (catalog remains). |
| `/timezone` | Show current timezone. |
| `/timezone Europe/Madrid` | Set IANA timezone. Unknown name is rejected. |
| `/test` | Send a test DAPNET page to enabled RIC callsigns. |
| `/refresh` | Sync enabled calendars now and list upcoming events (up to 15). |

### Help keyboard (approved)

| Button | Runs |
| --- | --- |
| Status | `/status` |
| Calendars | `/calendars` |
| Reminders | `/reminders` |
| TX groups | `/txgroup` |
| DAPNET core | `/server` |
| RICs | `/rics` |
| Timezone | `/timezone` (shows usage if you still need to type the zone) |
| Test page | `/test` |
| Refresh events | `/refresh` |
| Delete my data | `/delete` |

Timezone cannot be fully set from a button; send `/timezone Area/City`.

## Administrators only

Hidden from other users’ BotFather menu and `/help`.

| Command | What it does |
| --- | --- |
| `/pending` | Waiting registrations. |
| `/users` | Registered users (first 50). |
| `/approve <telegram_id>` | Approve. |
| `/reject <telegram_id>` | Reject. |

Help keyboard extras: **Pending**, **Users**. Registration notices include **Approve** / **Reject** buttons (`admin:approve:ID` / `admin:reject:ID`).

## Registration conversation (details)

| Step | You send | Next |
| --- | --- | --- |
| 1 | Callsign matching `^[a-z0-9/]{3,20}$` (case-insensitive) | DAPNET user + subscriber check |
| 2 | Spain or Germany button | RIC picker |
| 3 | Toggle RICs, type a number, or Done | Nextcloud URL |
| 3b | Owner callsign for a new RIC, or “use mine” | Back to RIC picker |
| 4 | Nextcloud URL | Username |
| 5 | Username | App password |
| 6 | App password (message deleted if possible) | Probe CalDAV, save, notify admins |

At least one RIC is required before **Done**.

## RIC menu limits

The on-screen RIC list shows at most **12** rows. Transmitter-group buttons show at most **18** names. Use `/rics 145904 CALLSIGN` if the button list is full.

## Status values you will see

| Status | Meaning |
| --- | --- |
| pending approval | Waiting for an admin. |
| approved | Sync and reminders allowed. |
| rejected | Blocked until a new `/register`. |
