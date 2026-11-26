"""Configuration and constants for User Protector Hub Support Bot."""

import os
from dotenv import load_dotenv

load_dotenv()

# Bot credentials
BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
OWNER_ID: int = int(os.getenv("OWNER_ID", "0"))

# Parse admin list from env
_admins_env = os.getenv("ADMINS", "")
ADMINS: list[int] = [int(x.strip()) for x in _admins_env.split(",") if x.strip().isdigit()]

# Database
DB_PATH: str = os.getenv("DB_PATH", "support.db")

# Branding
BRAND_NAME: str = "User Protector Hub"
SUPPORT_BOT_USERNAME: str = "@uphsupport_bot"

# Limits
RATE_LIMIT_SECONDS: int = int(os.getenv("RATE_LIMIT_SECONDS", "30"))
MAX_TICKETS_PER_DAY: int = int(os.getenv("MAX_TICKETS_PER_DAY", "3"))

# Logging
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

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
