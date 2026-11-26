"""Entry point for the User Protector Hub Support Bot."""

import logging
import sys

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

import config
import database as db
from handlers import admin as admin_h
from handlers import faq as faq_h
from handlers import fallback as fallback_h
from handlers import start as start_h
from handlers import ticket as ticket_h
from utils import report_error

logging.basicConfig(
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
)
logger = logging.getLogger(__name__)


async def error_handler(update: object, context) -> None:
    """Global error handler."""
    err = context.error
    logger.exception("Global handler error: %s", err)
    await report_error(context.bot, update if isinstance(update, Update) else None, err)


def build_ticket_conversation() -> ConversationHandler:
    """Build the user ticket conversation handler."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(ticket_h.start_ticket_flow, pattern=r"^ticket_new$"),
            CallbackQueryHandler(ticket_h.user_reply_start, pattern=r"^user_reply_"),
        ],
        states={
            config.TICKET_CATEGORY: [
                CallbackQueryHandler(ticket_h.choose_category, pattern=r"^cat_"),
                CallbackQueryHandler(ticket_h.cancel_ticket, pattern=r"^cancel_ticket$"),
            ],
            config.TICKET_MESSAGE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ticket_h.receive_message),
            ],
            config.TICKET_ATTACHMENT: [
                MessageHandler(
                    (filters.PHOTO | filters.Document.ALL) & ~filters.COMMAND,
                    ticket_h.receive_attachment,
                ),
                CallbackQueryHandler(ticket_h.skip_attachment, pattern=r"^skip_attachment$"),
                CallbackQueryHandler(ticket_h.cancel_ticket, pattern=r"^cancel_ticket$"),
            ],
            config.TICKET_CONFIRM: [
                CallbackQueryHandler(ticket_h.confirm_submit, pattern=r"^ticket_submit$"),
                CallbackQueryHandler(ticket_h.cancel_ticket, pattern=r"^cancel_ticket$"),
            ],
            config.TICKET_REPLY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, ticket_h.user_reply_send),
            ],
        },
        fallbacks=[CommandHandler("cancel", ticket_h.cancel_conversation)],
        allow_reentry=True,
    )


def build_admin_conversation() -> ConversationHandler:
    """Build the admin conversation handler."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(admin_h.admin_reply_start, pattern=r"^admin_reply_"),
            CallbackQueryHandler(admin_h.admin_close_callback, pattern=r"^admin_close_"),
            CallbackQueryHandler(admin_h.search_start, pattern=r"^admin_search$"),
            CallbackQueryHandler(admin_h.broadcast_start, pattern=r"^admin_broadcast$"),
        ],
        states={
            config.ADMIN_REPLY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_h.admin_reply_send),
            ],
            config.ADMIN_CLOSE_REASON: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_h.close_with_reason),
                CallbackQueryHandler(admin_h.close_now, pattern=r"^close_now_"),
            ],
            config.ADMIN_SEARCH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_h.search_query),
            ],
            config.ADMIN_BROADCAST: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_h.broadcast_preview),
            ],
        },
        fallbacks=[CommandHandler("cancel", admin_h.cancel_admin_flow)],
        allow_reentry=True,
    )


def register_handlers(app: Application) -> None:
    """Register all handlers."""
    # Commands
    app.add_handler(CommandHandler("start", start_h.start))
    app.add_handler(CommandHandler("help", start_h.help_command))
    app.add_handler(CommandHandler("about", start_h.about_command))
    app.add_handler(CommandHandler("mytickets", ticket_h.my_tickets_callback))
    app.add_handler(CommandHandler("admin", admin_h.admin_entry))
    app.add_handler(CommandHandler("close", admin_h.close_command))
    app.add_handler(CommandHandler("addadmin", admin_h.add_admin_command))
    app.add_handler(CommandHandler("rmadmin", admin_h.rm_admin_command))
    app.add_handler(CommandHandler("listadmins", admin_h.list_admins_command))

    # Conversations
    app.add_handler(build_ticket_conversation())
    app.add_handler(build_admin_conversation())

    # Menu callbacks
    app.add_handler(CallbackQueryHandler(start_h.main_menu_callback, pattern=r"^main_menu$"))
    app.add_handler(CallbackQueryHandler(start_h.about_callback, pattern=r"^about$"))
    app.add_handler(CallbackQueryHandler(start_h.contact_admin_callback, pattern=r"^contact_admin$"))
    app.add_handler(CallbackQueryHandler(start_h.noop_callback, pattern=r"^noop$"))

    # FAQ
    app.add_handler(CallbackQueryHandler(faq_h.faq_callback, pattern=r"^faq_\d+$"))

    # My tickets / view
    app.add_handler(CallbackQueryHandler(ticket_h.my_tickets_callback, pattern=r"^my_tickets$"))
    app.add_handler(CallbackQueryHandler(ticket_h.view_ticket_callback, pattern=r"^view_ticket_"))

    # Admin panel callbacks
    app.add_handler(CallbackQueryHandler(admin_h.admin_panel_callback, pattern=r"^admin_panel$"))
    app.add_handler(CallbackQueryHandler(admin_h.stats_callback, pattern=r"^admin_stats$"))
    app.add_handler(CallbackQueryHandler(admin_h.open_tickets_callback, pattern=r"^admin_open_tickets_\d+$"))
    app.add_handler(CallbackQueryHandler(admin_h.view_user_callback, pattern=r"^admin_view_"))
    app.add_handler(CallbackQueryHandler(admin_h.broadcast_confirm, pattern=r"^broadcast_confirm$"))

    # Fallback
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, fallback_h.fallback))

    # Error handler
    app.add_error_handler(error_handler)


def main() -> None:
    """Run the bot."""
    if not config.BOT_TOKEN:
        logger.critical("BOT_TOKEN is not set. Exiting.")
        sys.exit(1)
    db.init_db()
    logger.info("Starting %s support bot...", config.BRAND_NAME)
    application = Application.builder().token(config.BOT_TOKEN).build()
    register_handlers(application)
    application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    main()
