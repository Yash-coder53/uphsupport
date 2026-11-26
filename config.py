"""Configuration and constants for User Protector Hub Support Bot."""

import os

from dotenv import load_dotenv

load_dotenv()


def _env_int(name: str, default: int) -> int:
    """Read an integer env var safely. Falls back to default if empty or invalid."""
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


# Bot credentials
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()
OWNER_ID: int = _env_int("OWNER_ID", 0)

# Parse admin list from env (comma-separated Telegram user IDs)
_admins_env = os.getenv("ADMINS", "")
ADMINS: list[int] = []
for _x in _admins_env.split(","):
    _x = _x.strip()
    if _x.isascii() and _x.isdigit():
        ADMINS.append(int(_x))

# The owner is always an admin
if OWNER_ID and OWNER_ID not in ADMINS:
    ADMINS.append(OWNER_ID)

# Database
DB_PATH: str = os.getenv("DB_PATH", "support.db")

# Branding
BRAND_NAME: str = "User Protector Hub"
SUPPORT_BOT_USERNAME: str = "@uphsupport_bot"

# Limits
RATE_LIMIT_SECONDS: int = _env_int("RATE_LIMIT_SECONDS", 30)
MAX_TICKETS_PER_DAY: int = _env_int("MAX_TICKETS_PER_DAY", 3)

# Logging
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").strip().upper()


def validate_config() -> None:
    """Call once at startup (e.g. in main) to fail early with a clear message."""
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN is missing. Add BOT_TOKEN=your_token_from_BotFather to your .env file."
        )
    if not OWNER_ID:
        raise RuntimeError(
            "OWNER_ID is missing or invalid. Add OWNER_ID=your_numeric_telegram_id to your .env file."
        )


# Conversation states
(
    TICKET_CATEGORY,
    TICKET_MESSAGE,
    TICKET_ATTACHMENT,
    TICKET_CONFIRM,
    TICKET_REPLY,
    ADMIN_REPLY,
    ADMIN_BROADCAST,
    ADMIN_SEARCH,
    ADMIN_CLOSE_REASON,
) = range(9)

# Categories
CATEGORIES: list[tuple[str, str]] = [
    ("bug", "🐛 Bug"),
    ("report", "🚩 Report Issue"),
    ("account", "👤 Account"),
    ("other", "❓ Other"),
]

# FAQ content
FAQ_ITEMS: list[tuple[str, str]] = [
    (
        "What is the User Protector Hub reporting bot?",
        "The reporting bot is a separate Telegram bot that lets you report malicious users, "
        "scams, and harmful content. It's independent from this support bot. "
        "Our team reviews every report and takes appropriate action.",
    ),
    (
        "Is my data and privacy protected?",
        "Yes. We never share your personal information with third parties. "
        "Your support tickets and messages are only visible to our admin team. "
        "All data is stored securely and handled according to our privacy policy.",
    ),
    (
        "What happens if someone misuses the reporting bot?",
        "Misuse (false reports, spam) may result in temporary or permanent restrictions. "
        "We investigate every report carefully. If you believe you were wrongly flagged, "
        "create a support ticket and we'll review your case.",
    ),
    (
        "What evidence should I include in a report?",
        "Screenshots, message links, usernames, and timestamps are helpful. "
        "Include as much context as possible. Never include other people's private data "
        "beyond what's necessary to understand the issue.",
    ),
    (
        "How long does it take to process a report?",
        "Most reports are reviewed within 24-48 hours. Complex cases may take longer. "
        "You'll receive a notification once your report is processed.",
    ),
    (
        "Can I appeal a decision?",
        "Yes. If you believe a decision was incorrect, create a support ticket with "
        "category 'Report Issue' and include your report reference. Our team will re-review.",
    ),
    (
        "Is this bot affiliated with Telegram?",
        "No. User Protector Hub is an independent initiative and is not affiliated with, "
        "endorsed by, or connected to Telegram in any way.",
    ),
    (
        "How can I contact an admin directly?",
        "Use the '🎫 Create Support Ticket' option in the main menu. "
        "All tickets are routed to our admin team who will reply as soon as possible.",
    ),
]
