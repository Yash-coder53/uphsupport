"""Helper functions for formatting, validation, and logging."""

import logging
import traceback
from datetime import datetime
from typing import Optional

from telegram import Update
from telegram.error import BadRequest, Forbidden, RetryAfter

from config import BRAND_NAME, OWNER_ID

logger = logging.getLogger(__name__)

MAX_MESSAGE_LENGTH = 2000


def brand_header() -> str:
    """Return the standard brand header."""
    return f"🛡️ {BRAND_NAME} Support"


def truncate(text: str, limit: int = MAX_MESSAGE_LENGTH) -> str:
    """Truncate text to a maximum length."""
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


def validate_message(text: Optional[str], min_len: int = 3, max_len: int = 2000) -> tuple[bool, str]:
    """Validate a user-provided message."""
    if not text or not text.strip():
        return False, "Message cannot be empty."
    stripped = text.strip()
    if len(stripped) < min_len:
        return False, f"Message is too short (minimum {min_len} characters)."
    if len(stripped) > max_len:
        return False, f"Message is too long (maximum {max_len} characters)."
    return True, stripped


def format_datetime(iso_str: Optional[str]) -> str:
    """Format an ISO datetime string for display."""
    if not iso_str:
        return "—"
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except (ValueError, TypeError):
        return iso_str


def format_ticket(ticket) -> str:
    """Format a ticket row for display."""
    icon = "🟢" if ticket["status"] == "open" else "🔴"
    return (
        f"{icon} {ticket['ticket_code']} — {ticket['subject']}\n"
        f"Category: {ticket['category']}\n"
        f"Status: {ticket['status'].capitalize()}\n"
        f"Created: {format_datetime(ticket['created_at'])}"
    )


def format_ticket_full(ticket) -> str:
    """Full ticket detail view."""
    text = (
        f"🎫 {ticket['ticket_code']}\n"
        f"📌 Subject: {ticket['subject']}\n"
        f"📂 Category: {ticket['category']}\n"
        f"Status: {'🟢 Open' if ticket['status'] == 'open' else '🔴 Closed'}\n"
        f"Created: {format_datetime(ticket['created_at'])}\n"
    )
    if ticket["status"] == "closed" and ticket["closed_reason"]:
        text += f"Closed reason: {ticket['closed_reason']}\n"
    text += f"\n💬 Message:\n{ticket['message']}"
    return text


async def safe_send(bot, chat_id: int, text: str, **kwargs) -> bool:
    """Send a message, handling Forbidden/BadRequest/RetryAfter gracefully."""
    try:
        await bot.send_message(chat_id=chat_id, text=text, **kwargs)
        return True
    except Forbidden:
        logger.info("User %s has blocked the bot; skipping", chat_id)
        return False
    except RetryAfter as e:
        logger.warning("Rate limited by Telegram, retry after %s", e.retry_after)
        return False
    except BadRequest as e:
        logger.error("BadRequest sending to %s: %s", chat_id, e)
        return False
    except Exception as e:
        logger.error("Unexpected error sending to %s: %s", chat_id, e)
        return False


async def notify_owner(bot, text: str) -> None:
    """Notify the owner of critical errors."""
    if OWNER_ID:
        await safe_send(bot, OWNER_ID, truncate(text, 4000))


async def report_error(bot, update: Optional[Update], error: Exception) -> None:
    """Log an error and notify owner with traceback."""
    tb = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    logger.error("Handler error: %s\n%s", error, tb)
    if update and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ Something went wrong. Please try again later."
            )
        except Exception:
            pass
    await notify_owner(bot, f"⚠️ Bot error:\n{truncate(tb, 3500)}")


def category_label(key: str) -> str:
    """Human-readable category label."""
    from config import CATEGORIES
    for k, label in CATEGORIES:
        if k == key:
            return label
    return key.capitalize()
