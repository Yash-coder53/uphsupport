# 🛡️ User Protector Hub — Support Bot

An independent Telegram support bot for the **User Protector Hub** safety initiative.

Bot username: **@uphsupport_bot**

This bot handles user support — it is **not** the reporting bot. Its job is:
- Answering FAQs
- Collecting support tickets
- Letting admins reply to users via Telegram DMs
- Broadcasting messages to all users

---

## ✨ Features

### 👤 User Side
- `/start` — Main menu with inline buttons
- `/help` — List of all commands
- 📖 FAQ — 8 pre-written Q&A items with Back/Next navigation
- 🎫 Create Support Ticket — Guided multi-step form with optional screenshot
- 📋 My Tickets — View all your tickets with open/closed status
- 💬 Reply to ticket threads (admins are notified instantly)
- 📩 DM notification when an admin replies or closes a ticket

### 🛡️ Admin Side
- `/admin` — Admin panel: Stats, Open Tickets (paginated), Search, Broadcast
- 💬 Reply to new-ticket notifications directly from DM
- ✅ Close tickets with optional reason
- `/close <ticket_code> [reason]` — Quick close
- `/listadmins` — Show all admins
- `/addadmin <user_id>` — Owner only
- `/rmadmin <user_id>` — Owner only
- 📢 Broadcast to all bot users with progress feedback

### 🗄️ Database (SQLite: `support.db`)
- `users` — registered users
- `tickets` — support tickets with unique code `#UPH-0001`
- `messages` — message thread per ticket (user/admin)
- `admins` — dynamically-added admins

All queries are parameterized. Retries on lock.

---

## 🚀 Setup

### 1. Clone
```bash
git clone <your-repo-url> uph-support-bot
cd uph-support-bot
```

2. Install dependencies

```bash
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Create your bot via @BotFather

1. Open Telegram, message @BotFather
2. Send /newbot
3. Choose display name: User Protector Hub Support
4. Choose username: uphsupport_bot (or another if taken)
5. Copy the token BotFather gives you

4. Configure environment

Copy .env.example → .env and fill in:

```env
BOT_TOKEN=123456:ABC-YOUR-TOKEN-HERE
OWNER_ID=7267729758
ADMINS=123456789,987654321
DB_PATH=support.db
RATE_LIMIT_SECONDS=30
MAX_TICKETS_PER_DAY=3
LOG_LEVEL=INFO
```

· OWNER_ID — your Telegram numeric user ID (use @userinfobot)
· ADMINS — comma-separated IDs of initial admins (optional)

5. Run

```bash
python main.py
```

The SQLite database is created automatically on first run.

---

📖 Command Reference

User Commands

Command Description
/start Welcome message with main menu
/help Show all commands
/mytickets View your tickets
/cancel Cancel any active action

Admin Commands

Command Description
/admin Open the admin panel
/close <ticket> Close a ticket (optional reason)
/listadmins List all admins
/addadmin <user_id> Add an admin (owner only)
/rmadmin <user_id> Remove an admin (owner only)

---

📖 FAQ Content List

1. What is the User Protector Hub reporting bot?
2. Is my data and privacy protected?
3. What happens if someone misuses the reporting bot?
4. What evidence should I include in a report?
5. How long does it take to process a report?
6. Can I appeal a decision?
7. Is this bot affiliated with Telegram?
8. How can I contact an admin directly?

---

🔒 Security & Reliability

· Parameterized SQL queries only — no SQL injection
· Retry logic on database is locked
· Graceful handling of Forbidden, BadRequest, RetryAfter
· Rate limiting — 1 ticket per 30s, 3 tickets/day per user
· Global error handler — notifies the OWNER with full traceback
· Blocked users are skipped without crashing
· No hardcoded secrets — everything comes from .env

---

⚠️ Disclaimer

User Protector Hub is an independent initiative and is not affiliated, endorsed, or connected with Telegram, its subsidiaries, or partners in any way. Use at your own discretion.

---

📄 License

MIT License

Copyright (c) 2025 User Protector Hub

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files, to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND.

```

---

## ✅ Quick Start Summary

1. `pip install -r requirements.txt`
2. Copy `.env.example` → `.env`, set `BOT_TOKEN` and `OWNER_ID`
3. `python main.py` — done!

The bot starts, creates `support.db`, and responds to `/start`. All admin DM notifications, ticket threads, and broadcast flows work out of the box.

Bhai, yeh bot **pura complete** hai — har file alag, sab handlers wired, database retry logic, rate limiting, global error reporting, admin panel, broadcast with progress, aur gracefully blocked-user handling. Koi placeholder nahi, koi truncation nahi. Just token daalo aur run karo. 🚀
