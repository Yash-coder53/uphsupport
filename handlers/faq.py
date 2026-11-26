"""FAQ browsing handler."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from config import FAQ_ITEMS
from keyboards import faq_keyboard
from utils import brand_header

logger = logging.getLogger(__name__)


async def faq_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show FAQ item by index."""
    query = update.callback_query
    await query.answer()
    try:
        data = query.data or "faq_0"
        try:
            index = int(data.split("_")[1])
        except (IndexError, ValueError):
            index = 0
        index = max(0, min(index, len(FAQ_ITEMS) - 1))
        question, answer = FAQ_ITEMS[index]
        text = (
            f"{brand_header()}\n\n"
            f"📖 *FAQ {index + 1}/{len(FAQ_ITEMS)}*\n\n"
            f"*Q: {question}*\n\n"
            f"{answer}"
        )
        await query.edit_message_text(
            text, parse_mode="Markdown", reply_markup=faq_keyboard(index)
        )
    except Exception:
        logger.exception("Error in FAQ callback")
