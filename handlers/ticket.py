"""Ticket creation, listing, and user reply handlers."""

import logging
import time
from datetime import datetime

from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
)

import database as db
from config import (
    MAX_TICKETS_PER_DAY,
    RATE_LIMIT_SECONDS,
    TICKET_ATTACHMENT,
    TICKET_CATEGORY,
    TICKET_CONFIRM,
    TICKET_MESSAGE,
    TICKET_REPLY,
)
from keyboards import (
    category_keyboard,
    confirm_ticket_keyboard,
    main_menu_keyboard,
    my_tickets_keyboard,
    skip_attachment_keyboard,
    ticket_actions_keyboard,
    ticket_detail_keyboard,
    user_reply_back_keyboard,
)
from utils import (
    brand_header,
    category_label,
    format_ticket_full,
    safe_send,
    validate_message,
)

logger = logging.getLogger(__name__)

# In-memory rate limiting: {user_id: last_ticket_time}
_last_ticket_time: dict[int, float] = {}


def _check_rate_limit(user_id: int) -> tuple[bool, str]:
    """Check both daily-count and per-30s rate limits."""
    last = _last_ticket_time.get(user_id, 0)
    if time.time() - last < RATE_LIMIT_SECONDS:
        remaining = int(RATE_LIMIT_SECONDS - (time.time() - last))
        return False, f"⚠️ Please wait {remaining}s before creating another ticket."
    if db.user_tickets_today(user_id) >= MAX_TICKETS_PER_DAY:
        return False, f"⚠️ You've reached the daily limit of {MAX_TICKETS_PER_DAY} tickets."
    return True, ""


async def start_ticket_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point: start ticket creation."""
    query = update.callback_query
    await query.answer()
    try:
        user = update.effective_user
        db.upsert_user(user.id, user.username, user.first_name)
        allowed, reason = _check_rate_limit(user.id)
        if not allowed:
            await query.edit_message_text(reason, reply_markup=main_menu_keyboard())
            return ConversationHandler.END
        context.user_data["ticket_draft"] = {}
        await query.edit_message_text(
            f"{brand_header()}\n\n"
            "🎫 *Create Support Ticket*\n\n"
            "Step 1/4: Please choose a category 👇",
            parse_mode="Markdown",
            reply_markup=category_keyboard(),
        )
        return TICKET_CATEGORY
    except Exception:
        logger.exception("Error starting ticket flow")
        return ConversationHandler.END


async def choose_category(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store the chosen category, ask for subject/message."""
    query = update.callback_query
    await query.answer()
    try:
        data = query.data or ""
        category = data.replace("cat_", "")
        context.user_data.setdefault("ticket_draft", {})["category"] = category
        await query.edit_message_text(
            f"{brand_header()}\n\n"
            f"📂 Category: *{category_label(category)}*\n\n"
            "Step 2/4: Please describe your issue in detail.\n"
            "Include a short subject on the first line if you like.\n\n"
            "_(Send /cancel to abort)_",
            parse_mode="Markdown",
        )
        return TICKET_MESSAGE
    except Exception:
        logger.exception("Error in choose_category")
        return TICKET_MESSAGE


async def receive_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store the message text, ask for attachment."""
    try:
        text = update.message.text or ""
        ok, result = validate_message(text, min_len=5, max_len=2000)
        if not ok:
            await update.message.reply_text(
                f"❌ {result}\n\nPlease try again or /cancel."
            )
            return TICKET_MESSAGE
        draft = context.user_data.setdefault("ticket_draft", {})
        # First line becomes subject, whole text becomes message
        first_line = result.splitlines()[0].strip()
        draft["subject"] = first_line[:80] if first_line else "Support request"
        draft["message"] = result
        await update.message.reply_text(
            f"{brand_header()}\n\n"
            "Step 3/4: You may attach a screenshot or photo. 📸\n\n"
            "Send it now, or tap *Skip* to continue.",
            parse_mode="Markdown",
            reply_markup=skip_attachment_keyboard(),
        )
        return TICKET_ATTACHMENT
    except Exception:
        logger.exception("Error in receive_message")
        return TICKET_MESSAGE


async def receive_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Store a photo/file_id if a photo is sent."""
    try:
        draft = context.user_data.setdefault("ticket_draft", {})
        if update.message.photo:
            draft["attachment_file_id"] = update.message.photo[-1].file_id
            draft["attachment_type"] = "photo"
            note = "✅ Screenshot attached."
        elif update.message.document:
            draft["attachment_file_id"] = update.message.document.file_id
            draft["attachment_type"] = "document"
            note = "✅ Document attached."
        else:
            note = "⚠️ Unsupported attachment type — skipped."
        await update.message.reply_text(note)
        return await _ask_confirm(update, context)
    except Exception:
        logger.exception("Error in receive_attachment")
        return TICKET_ATTACHMENT


async def skip_attachment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Skip attachment step."""
    query = update.callback_query
    await query.answer()
    try:
        return await _ask_confirm(update, context, use_query=True)
    except Exception:
        logger.exception("Error in skip_attachment")
        return TICKET_ATTACHMENT


async def _ask_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, use_query: bool = False) -> int:
    """Show a preview and ask for confirmation."""
    draft = context.user_data.get("ticket_draft", {})
    preview = (
        f"{brand_header()}\n\n"
        "Step 4/4: Please confirm your ticket 👇\n\n"
        f"📂 Category: *{category_label(draft.get('category', 'other'))}*\n"
        f"📌 Subject: {draft.get('subject', '—')}\n"
        f"💬 Message: {draft.get('message', '—')[:400]}\n"
        f"📎 Attachment: {'Yes' if draft.get('attachment_file_id') else 'No'}\n\n"
        "Submit this ticket?"
    )
    if use_query:
        await update.callback_query.edit_message_text(
            preview, parse_mode="Markdown", reply_markup=confirm_ticket_keyboard()
        )
    else:
        await update.message.reply_text(
            preview, parse_mode="Markdown", reply_markup=confirm_ticket_keyboard()
        )
    return TICKET_CONFIRM


async def confirm_submit(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Create the ticket and notify admins."""
    query = update.callback_query
    await query.answer()
    try:
        user = update.effective_user
        draft = context.user_data.get("ticket_draft", {})
        if not draft.get("message"):
            await query.edit_message_text(
                "❌ Draft missing. Please restart.", reply_markup=main_menu_keyboard()
            )
            return ConversationHandler.END

        ticket_code = db.create_ticket(
            user_id=user.id,
            category=draft.get("category", "other"),
            subject=draft.get("subject", "Support request"),
            message=draft["message"],
        )
        _last_ticket_time[user.id] = time.time()
        db.add_message(
            ticket_id=db.get_ticket_by_code(ticket_code)["id"],
            sender_id=user.id,
            sender_type="user",
            text=draft["message"],
        )
        await query.edit_message_text(
            f"{brand_header()}\n\n"
            f"✅ Ticket created successfully!\n\n"
            f"🎫 Ticket ID: *{ticket_code}*\n"
            "Our team will reply shortly. You'll be notified here.\n\n"
            "Use /mytickets to check status anytime.",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )
        await _notify_admins_new_ticket(context, ticket_code, user, draft)
        context.user_data.pop("ticket_draft", None)
        return ConversationHandler.END
    except Exception:
        logger.exception("Error in confirm_submit")
        return ConversationHandler.END


async def _notify_admins_new_ticket(context: ContextTypes.DEFAULT_TYPE, ticket_code: str, user, draft: dict) -> None:
    """Send new-ticket notification to all admins."""
    admin_text = (
        f"{brand_header()}\n\n"
        f"🆕 *New Ticket* {ticket_code}\n\n"
        f"👤 User: {user.first_name or '—'} (@{user.username or 'no username'})\n"
        f"🆔 ID: `{user.id}`\n"
        f"📂 Category: {category_label(draft.get('category', 'other'))}\n"
        f"📌 Subject: {draft.get('subject', '—')}\n\n"
        f"💬 Message:\n{draft['message'][:1500]}"
    )
    for admin_id in db.get_admins():
        await safe_send(
            context.bot,
            admin_id,
            admin_text,
            parse_mode="Markdown",
            reply_markup=ticket_actions_keyboard(ticket_code),
        )
        if draft.get("attachment_file_id"):
            try:
                if draft.get("attachment_type") == "photo":
                    await context.bot.send_photo(
                        chat_id=admin_id, photo=draft["attachment_file_id"]
                    )
                else:
                    await context.bot.send_document(
                        chat_id=admin_id, document=draft["attachment_file_id"]
                    )
            except Exception:
                logger.warning("Failed to forward attachment to admin %s", admin_id)


async def cancel_ticket(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel the ticket flow."""
    query = update.callback_query
    if query:
        await query.answer()
        try:
            await query.edit_message_text(
                "❌ Ticket creation cancelled.", reply_markup=main_menu_keyboard()
            )
        except Exception:
            pass
    else:
        await update.message.reply_text(
            "❌ Ticket creation cancelled.", reply_markup=main_menu_keyboard()
        )
    context.user_data.pop("ticket_draft", None)
    return ConversationHandler.END


async def my_tickets_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List user's tickets."""
    query = update.callback_query
    await query.answer()
    try:
        user = update.effective_user
        tickets = db.get_user_tickets(user.id)
        if not tickets:
            await query.edit_message_text(
                f"{brand_header()}\n\n"
                "📋 You have no tickets yet.\n\n"
                "Create one via 🎫 Create Support Ticket from the main menu.",
                reply_markup=main_menu_keyboard(),
            )
            return
        await query.edit_message_text(
            f"{brand_header()}\n\n📋 *Your Tickets*\n\nTap one to view details:",
            parse_mode="Markdown",
            reply_markup=my_tickets_keyboard(tickets),
        )
    except Exception:
        logger.exception("Error in my_tickets")


async def view_ticket_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show ticket detail."""
    query = update.callback_query
    await query.answer()
    try:
        ticket_code = (query.data or "").replace("view_ticket_", "")
        ticket = db.get_ticket_by_code(ticket_code)
        user = update.effective_user
        if not ticket or ticket["user_id"] != user.id:
            await query.edit_message_text(
                "❌ Ticket not found.", reply_markup=main_menu_keyboard()
            )
            return
        is_open = ticket["status"] == "open"
        await query.edit_message_text(
            format_ticket_full(ticket),
            reply_markup=ticket_detail_keyboard(ticket_code, is_open),
        )
    except Exception:
        logger.exception("Error viewing ticket")


async def user_reply_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """User taps Reply on their own ticket → prompt to type message."""
    query = update.callback_query
    await query.answer()
    try:
        ticket_code = (query.data or "").replace("user_reply_", "")
        ticket = db.get_ticket_by_code(ticket_code)
        if not ticket or ticket["user_id"] != update.effective_user.id:
            await query.edit_message_text(
                "❌ Ticket not found.", reply_markup=main_menu_keyboard()
            )
            return ConversationHandler.END
        if ticket["status"] != "open":
            await query.edit_message_text(
                "🔴 This ticket is closed. Create a new ticket if you need help.",
                reply_markup=main_menu_keyboard(),
            )
            return ConversationHandler.END
        context.user_data["reply_ticket"] = ticket_code
        await query.edit_message_text(
            f"{brand_header()}\n\n"
            f"💬 Replying to *{ticket_code}*.\n\n"
            "Type your message below (or /cancel).",
            parse_mode="Markdown",
        )
        return TICKET_REPLY
    except Exception:
        logger.exception("Error starting user reply")
        return ConversationHandler.END


async def user_reply_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send user's reply to admins."""
    try:
        ticket_code = context.user_data.get("reply_ticket")
        if not ticket_code:
            await update.message.reply_text(
                "❌ No active ticket.", reply_markup=main_menu_keyboard()
            )
            return ConversationHandler.END
        ok, result = validate_message(update.message.text or "", min_len=1, max_len=2000)
        if not ok:
            await update.message.reply_text(f"❌ {result}\nTry again or /cancel.")
            return TICKET_REPLY
        ticket = db.get_ticket_by_code(ticket_code)
        if not ticket or ticket["status"] != "open":
            await update.message.reply_text(
                "❌ Ticket is closed or missing.", reply_markup=main_menu_keyboard()
            )
            return ConversationHandler.END
        db.add_message(ticket["id"], update.effective_user.id, "user", result)
        await update.message.reply_text(
            f"✅ Reply sent to admins for {ticket_code}.",
            reply_markup=user_reply_back_keyboard(ticket_code),
        )
        user = update.effective_user
        admin_text = (
            f"{brand_header()}\n\n"
            f"💬 *New reply on* {ticket_code}\n"
            f"👤 From: {user.first_name or '—'} (@{user.username or 'no username'})\n"
            f"🆔 `{user.id}`\n\n{result[:1500]}"
        )
        for admin_id in db.get_admins():
            await safe_send(
                context.bot,
                admin_id,
                admin_text,
                parse_mode="Markdown",
                reply_markup=ticket_actions_keyboard(ticket_code),
            )
        context.user_data.pop("reply_ticket", None)
        return ConversationHandler.END
    except Exception:
        logger.exception("Error sending user reply")
        return ConversationHandler.END


async def cancel_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Generic /cancel."""
    context.user_data.pop("ticket_draft", None)
    context.user_data.pop("reply_ticket", None)
    if update.callback_query:
        await update.callback_query.answer()
        try:
            await update.callback_query.edit_message_text(
                "❌ Cancelled.", reply_markup=main_menu_keyboard()
            )
        except Exception:
            pass
    else:
        await update.message.reply_text(
            "❌ Cancelled.", reply_markup=main_menu_keyboard()
        )
    return ConversationHandler.END
