"""Fallback handler for unknown messages."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from keyboards import main_menu_keyboard
from utils import brand_header

logger = logging.getLogger(__name__)


async def fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Catch anything not handled elsewhere."""
    try:
        if not update.message:
            return
        await update.message.reply_text(
            f"{brand_header()}\n\n"
            "🤔 I didn't understand that.\n\n"
            "Please use the menu below, or type /help for a command list.",
            reply_markup=main_menu_keyboard(),
        )
    except Exception:
        logger.exception("Fallback error")
