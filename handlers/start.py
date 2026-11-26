"""Start, help, about, and main menu handlers."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

import database as db
from config import BRAND_NAME
from keyboards import back_to_menu_keyboard, main_menu_keyboard
from utils import brand_header

logger = logging.getLogger(__name__)

WELCOME_TEXT = (
    f"{brand_header()}\n\n"
    f"Welcome to {BRAND_NAME} support! 🛡️\n\n"
    "I'm here to help you with:\n"
    "• Answering your questions (FAQ)\n"
    "• Creating and tracking support tickets\n"
    "• Connecting you with our admin team\n\n"
    "Choose an option below to get started 👇"
)

HELP_TEXT = (
    f"{brand_header()}\n\n"
    "📖 *Available Commands*\n\n"
    "👤 *For Users:*\n"
    "/start — Open main menu\n"
    "/help — Show this help\n"
    "/mytickets — View your tickets\n"
    "/cancel — Cancel current action\n\n"
    "🛡️ *For Admins:*\n"
    "/admin — Admin panel\n"
    "/close <ticket_id> — Close a ticket\n"
    "/listadmins — Show admin list\n"
    "/addadmin <user_id> — Add admin (owner only)\n"
    "/rmadmin <user_id> — Remove admin (owner only)\n\n"
    "Use the buttons below or the main menu for quick access."
)

ABOUT_TEXT = (
    f"{brand_header()}\n\n"
    f"*About {BRAND_NAME}*\n\n"
    f"{BRAND_NAME} is an independent Telegram safety initiative dedicated to "
    "keeping users safe from scams, malicious actors, and harmful content.\n\n"
    "🛡️ *What we do:*\n"
    "• Review reports of malicious users\n"
    "• Provide guidance and support\n"
    "• Maintain community safety standards\n\n"
    "⚠️ *Disclaimer:*\n"
    f"{BRAND_NAME} is an independent initiative and is *not affiliated* with "
    "Telegram, its subsidiaries, or partners.\n\n"
    "Use /help to see all commands."
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    try:
        user = update.effective_user
        if user:
            db.upsert_user(user.id, user.username, user.first_name)
        await update.message.reply_text(
            WELCOME_TEXT, reply_markup=main_menu_keyboard()
        )
    except Exception:
        logger.exception("Error in start handler")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /help command."""
    try:
        await update.message.reply_text(
            HELP_TEXT, parse_mode="Markdown", reply_markup=back_to_menu_keyboard()
        )
    except Exception:
        logger.exception("Error in help handler")


async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /about command."""
    try:
        await update.message.reply_text(
            ABOUT_TEXT, parse_mode="Markdown", reply_markup=back_to_menu_keyboard()
        )
    except Exception:
        logger.exception("Error in about handler")


async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return to the main menu."""
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_text(
            WELCOME_TEXT, reply_markup=main_menu_keyboard()
        )
    except Exception:
        logger.exception("Error showing main menu")


async def about_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show About Us from button."""
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_text(
            ABOUT_TEXT, parse_mode="Markdown", reply_markup=back_to_menu_keyboard()
        )
    except Exception:
        logger.exception("Error showing about")


async def contact_admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Prompt user to create a ticket to contact admins."""
    query = update.callback_query
    await query.answer()
    try:
        await query.edit_message_text(
            f"{brand_header()}\n\n"
            "📞 *Contact Admin*\n\n"
            "The best way to reach our admin team is by creating a support ticket. "
            "Click the button below to start.\n\n"
            "All tickets are reviewed by real humans — usually within 24 hours.",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )
    except Exception:
        logger.exception("Error in contact admin")


async def noop_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Acknowledge placeholder buttons."""
    await update.callback_query.answer()
