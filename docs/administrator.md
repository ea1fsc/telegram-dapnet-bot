# Administrator guide

Administrators are Telegram users whose **numeric ids** appear in `ADMIN_TELEGRAM_IDS`. They do not need shell access. They only need to have started a private chat with the bot.

If you also host the process, read the [Operator guide](operator.md) first.

## What you approve

Every new registration (and any re-registration that **changes** the DAPNET callsign) lands in status **pending**. Until you approve:

- `/calendars`, `/reminders`, `/txgroup`, `/server`, `/rics`, `/timezone`, `/test`, and `/refresh` are blocked;
- `/status` and `/delete` still work.

If someone re-registers with the **same** callsign while already approved, they stay approved (credentials and RICs update). You will **not** get a new notice in that case.

## New-registration notice

When a user completes `/register`, each admin receives a plain-text message:

```
New registration request
Telegram: @username (123456789)
Callsign: EA1ABC
RIC: 145904,145905
Core: Spain (dapnet.es)
Nextcloud: https://cloud.example.org/remote.php/dav (alice)
```

Buttons: **Approve** | **Reject**.

The notice includes the Nextcloud URL and username so you can sanity-check the instance. It does **not** include the app password.

If you never receive notices:

- you have not sent `/start` to the bot;
- your Telegram id is not in `ADMIN_TELEGRAM_IDS` (restart after editing `.env`);
- the bot cannot message you (you blocked it).

Failed admin notifies are logged; the user’s registration is still stored as pending.

## Commands

Admin commands appear in `/help` and in the Telegram command menu **only** in admin chats. Other users who type them get: `I do not know that command. Use /help for the command menu.`

| Command | What it does |
| --- | --- |
| `/pending` | List waiting registrations: Telegram id, callsign, `@username`, RIC CSV if present. Empty: `There are no pending requests.` |
| `/users` | List registered users (up to **50**): Telegram id, callsign, `[pending\|approved\|rejected]`. |
| `/approve <telegram_id>` | Set status to approved. |
| `/reject <telegram_id>` | Set status to rejected. |

Examples:

```
/approve 123456789
/reject 123456789
```

The id must be numeric. Wrong id: `I could not find that user.` Missing argument: `Usage: /approve <telegram_id>`.

You can also tap **Pending** and **Users** on your `/help` keyboard.

## What the user is told

- **Approved:** they get a Telegram message telling them to use `/help`, pick calendars with `/calendars`, and destination RICs with `/rics`. Pages and Telegram reminders will follow events.
- **Rejected:** they are told they can `/register` again if that was a mistake.

If Telegram cannot deliver that DM (user blocked the bot), you still see `User 123456789 (ea1abc) approved.` (or `rejected`) in your chat.

## Review checklist (suggested)

Before you approve, confirm:

1. You know the person (club member, yourself, etc.). Their Nextcloud credentials will live on the operator’s server.
2. The callsign is a real ham call you expect.
3. The Nextcloud URL looks like a server they own or are allowed to use (`https://…`, not a random host).
4. RIC list is not empty in the notice (registration requires at least one RIC, but it is worth a glance).

There is no “inspect calendars before approve” command. Approval only unlocks CalDAV polling for calendars they later turn **ON**.

## After approval

You do not manage their calendars, timezone, or transmitter groups. That is the [user guide](user-guide.md).

There is no `/revoke` command. To remove access:

- `/reject <telegram_id>` — they keep stored credentials but cannot sync; they may `/register` again;
- ask them to `/delete`, or delete their row in SQLite if you have operator access (see [Security](security.md)).

`/users` does not paginate past 50 people. For larger deployments query SQLite as the operator.

## Admins who also use the bot

An admin can `/register` like anyone else. Their own account still needs approval **unless** another admin approves them (or they `/approve` their own Telegram id). Self-approval via `/approve YOUR_ID` works if you are listed in `ADMIN_TELEGRAM_IDS`.
