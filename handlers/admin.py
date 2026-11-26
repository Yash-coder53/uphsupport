"""Admin handlers: panel, reply, close, stats, broadcast, search, admins management."""

import asyncio
import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

import database as db
from config import (
    ADMIN_BROADCAST,
    ADMIN_CLOSE_REASON,
    ADMIN_REPLY,
    ADMIN_SEARCH,
    BRAND_NAME,
    OWNER_ID,
)
from keyboards import (
    admin_panel_keyboard,
    back_to_menu_keyboard,
    broadcast_confirm_keyboard,
    close_confirm_keyboard,
    main_menu_keyboard,
    pagination_keyboard,
    ticket_actions_keyboard,
    user_reply_back_keyboard,
)
from utils import (
    brand_header,
    category_label,
    format_datetime,
    format_ticket,
    format_ticket_full,
    safe_send,
    validate_message,
)

logger = logging.getLogger(__name__)

PAGE_SIZE = 5


def _require_admin(update: Update) -> bool:
    """Return True if the caller is an admin."""
    user = update.effective_user
    return bool(user and db.is_admin(user.id))


async def admin_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /admin command or callback."""
    if not _require_admin(update):
        msg = "❌ You're not authorized."
        if update.callback_query:
            await update.callback_query.answer(msg, show_alert=True)
        else:
            await update.message.reply_text(msg)
        return
    text = f"{brand_header()}\n\n🛡️ *Admin Panel*\n\nChoose an action:"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text, parse_mode="Markdown", reply_markup=admin_panel_keyboard()
        )
    else:
        await update.message.reply_text(
            text, parse_mode="Markdown", reply_markup=admin_panel_keyboard()
        )


async def stats_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show ticket stats."""
    query = update.callback_query
    await query.answer()
    if not _require_admin(update):
        return
    try:
        s = db.get_stats()
        text = (
            f"{brand_header()}\n\n"
            "📊 *Statistics*\n\n"
            f"🎫 Total tickets: {s['total']}\n"
            f"🟢 Open: {s['open']}\n"
            f"🔴 Closed: {s['closed']}\n"
            f"📅 Today: {s['today']}\n"
            f"👥 Users: {s['users']}"
        )
        await query.edit_message_text(
            text, parse_mode="Markdown", reply_markup=admin_panel_keyboard()
        )
    except Exception:
        logger.exception("Stats error")


async def open_tickets_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show paginated open tickets."""
    query = update.callback_query
    await query.answer()
    if not _require_admin(update):
        return
    try:
        data = query.data or "admin_open_tickets_0"
        try:
            page = int(data.split("_")[-1])
        except ValueError:
            page = 0
        offset = page * PAGE_SIZE
        tickets = db.get_open_tickets(limit=PAGE_SIZE + 1, offset=offset)
        has_next = len(tickets) > PAGE_SIZE
        tickets = tickets[:PAGE_SIZE]
        if not tickets:
            await query.edit_message_text(
                "📭 No open tickets.",
                reply_markup=pagination_keyboard("admin_open_tickets_", page, False),
            )
            return
        lines = [f"{brand_header()}\n\n🎫 *Open Tickets* (page {page + 1})\n"]
        for t in tickets:
            lines.append(
                f"• {t['ticket_code']} — {t['subject']}  ({category_label(t['category'])})\n"
                f"  👤 user `{t['user_id']}`"
            )
        await query.edit_message_text(
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=pagination_keyboard("admin_open_tickets_", page, has_next),
        )
    except Exception:
        logger.exception("Open tickets error")


async def admin_reply_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin taps Reply on a ticket."""
    query = update.callback_query
    await query.answer()
    if not _require_admin(update):
        return ConversationHandler.END
    try:
        ticket_code = (query.data or "").replace("admin_reply_", "")
        ticket = db.get_ticket_by_code(ticket_code)
        if not ticket:
            await query.edit_message_text("❌ Ticket not found.")
            return ConversationHandler.END
        if ticket["status"] != "open":
            await query.edit_message_text(
                f"🔴 {ticket_code} is already closed.", reply_markup=admin_panel_keyboard()
            )
            return ConversationHandler.END
        context.user_data["admin_reply_ticket"] = ticket_code
        await query.edit_message_text(
            f"{brand_header()}\n\n"
            f"💬 *Replying to* {ticket_code}\n\n"
            "Type your reply message (or /cancel).",
            parse_mode="Markdown",
        )
        return ADMIN_REPLY
    except Exception:
        logger.exception("admin_reply_start error")
        return ConversationHandler.END


async def admin_reply_send(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Send admin's reply to user."""
    if not _require_admin(update):
        return ConversationHandler.END
    try:
        ticket_code = context.user_data.get("admin_reply_ticket")
        if not ticket_code:
            await update.message.reply_text("❌ No active ticket.")
            return ConversationHandler.END
        ok, result = validate_message(update.message.text or "", min_len=1, max_len=2000)
        if not ok:
            await update.message.reply_text(f"❌ {result}\nTry again or /cancel.")
            return ADMIN_REPLY
        ticket = db.get_ticket_by_code(ticket_code)
        if not ticket:
            await update.message.reply_text("❌ Ticket gone.")
            return ConversationHandler.END
        if ticket["status"] != "open":
            await update.message.reply_text("🔴 Ticket closed.")
            return ConversationHandler.END
        db.add_message(ticket["id"], update.effective_user.id, "admin", result)
        user_text = (
            f"{brand_header()}\n\n"
            f"📩 *Admin reply* for {ticket_code}\n\n"
            f"{result}\n\n"
            "You can reply back using the button below."
        )
        sent = await safe_send(
            context.bot,
            ticket["user_id"],
            user_text,
            parse_mode="Markdown",
            reply_markup=user_reply_back_keyboard(ticket_code),
        )
        if sent:
            await update.message.reply_text(
                f"✅ Reply sent for {ticket_code}.", reply_markup=admin_panel_keyboard()
            )
        else:
            await update.message.reply_text(
                f"⚠️ Could not deliver to user {ticket['user_id']} "
                "(they may have blocked the bot).",
                reply_markup=admin_panel_keyboard(),
            )
        context.user_data.pop("admin_reply_ticket", None)
        return ConversationHandler.END
    except Exception:
        logger.exception("admin_reply_send error")
        return ConversationHandler.END


async def admin_close_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Admin presses Close on a ticket notification."""
    query = update.callback_query
    await query.answer()
    if not _require_admin(update):
        return ConversationHandler.END
    try:
        ticket_code = (query.data or "").replace("admin_close_", "")
        ticket = db.get_ticket_by_code(ticket_code)
        if not ticket:
            await query.edit_message_text("❌ Ticket not found.")
            return ConversationHandler.END
        if ticket["status"] == "closed":
            await query.edit_message_text(f"🔴 {ticket_code} already closed.")
            return ConversationHandler.END
        context.user_data["close_ticket"] = ticket_code
        await query.edit_message_text(
            f"{brand_header()}\n\n"
            f"Close *{ticket_code}*?\n\n"
            "You can type a reason (or tap the button to close without reason).",
            parse_mode="Markdown",
            reply_markup=close_confirm_keyboard(ticket_code),
        )
        return ADMIN_CLOSE_REASON
    except Exception:
        logger.exception("admin_close_callback error")
        return ConversationHandler.END


async def close_now(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Close without typing a reason."""
    query = update.callback_query
    await query.answer()
    if not _require_admin(update):
        return ConversationHandler.END
    try:
        ticket_code = (query.data or "").replace("close_now_", "")
        await _do_close(context, ticket_code, "")
        await query.edit_message_text(
            f"✅ {ticket_code} closed.", reply_markup=admin_panel_keyboard()
        )
        context.user_data.pop("close_ticket", None)
        return ConversationHandler.END
    except Exception:
        logger.exception("close_now error")
        return ConversationHandler.END


async def close_with_reason(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Close with typed reason."""
    if not _require_admin(update):
        return ConversationHandler.END
    try:
        ticket_code = context.user_data.get("close_ticket")
        if not ticket_code:
            await update.message.reply_text("❌ No ticket.")
            return ConversationHandler.END
        reason = (update.message.text or "").strip()[:300]
        await _do_close(context, ticket_code, reason)
        await update.message.reply_text(
            f"✅ {ticket_code} closed.", reply_markup=admin_panel_keyboard()
        )
        context.user_data.pop("close_ticket", None)
        return ConversationHandler.END
    except Exception:
        logger.exception("close_with_reason error")
        return ConversationHandler.END


async def _do_close(context: ContextTypes.DEFAULT_TYPE, ticket_code: str, reason: str) -> None:
    """Internal: close a ticket and notify user."""
    ticket = db.get_ticket_by_code(ticket_code)
    if not ticket:
        return
    if not db.close_ticket(ticket_code, reason):
        return
    user_text = (
        f"{brand_header()}\n\n"
        f"🔴 Your ticket *{ticket_code}* has been closed.\n\n"
        + (f"Reason: {reason}\n\n" if reason else "")
        + "If you need further help, feel free to create a new ticket."
    )
    await safe_send(
        context.bot,
        ticket["user_id"],
        user_text,
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


async def close_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /close <ticket_code> [reason]."""
    if not _require_admin(update):
        await update.message.reply_text("❌ Unauthorized.")
        return
    try:
        args = context.args or []
        if not args:
            await update.message.reply_text("Usage: /close <ticket_code> [reason]")
            return
        ticket_code = args[0]
        if not ticket_code.startswith("#"):
            ticket_code = f"#{ticket_code}"
        reason = " ".join(args[1:])[:300]
        ticket = db.get_ticket_by_code(ticket_code)
        if not ticket:
            await update.message.reply_text(f"❌ Ticket {ticket_code} not found.")
            return
        await _do_close(context, ticket_code, reason)
        await update.message.reply_text(
            f"✅ {ticket_code} closed.", reply_markup=admin_panel_keyboard()
        )
    except Exception:
        logger.exception("close_command error")


async def view_user_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show ticket's user info."""
    query = update.callback_query
    await query.answer()
    if not _require_admin(update):
        return
    try:
        ticket_code = (query.data or "").replace("admin_view_", "")
        ticket = db.get_ticket_by_code(ticket_code)
        if not ticket:
            await query.edit_message_text("❌ Ticket not found.")
            return
        user = db.get_user(ticket["user_id"])
        if not user:
            await query.edit_message_text("❌ User not found.")
            return
        text = (
            f"{brand_header()}\n\n"
            f"👤 *User Info*\n\n"
            f"ID: `{user['user_id']}`\n"
            f"Name: {user['first_name'] or '—'}\n"
            f"Username: @{user['username'] or 'none'}\n"
            f"Joined: {format_datetime(user['joined_at'])}"
        )
        await query.edit_message_text(text, parse_mode="Markdown")
    except Exception:
        logger.exception("view_user_callback error")


async def search_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Prompt for ticket code search."""
    query = update.callback_query
    await query.answer()
    if not _require_admin(update):
        return ConversationHandler.END
    try:
        await query.edit_message_text(
            f"{brand_header()}\n\n🔍 Enter the ticket code to search (e.g. #UPH-0001)."
        )
        return ADMIN_SEARCH
    except Exception:
        logger.exception("search_start error")
        return ConversationHandler.END


async def search_query(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Look up a ticket by code."""
    if not _require_admin(update):
        return ConversationHandler.END
    try:
        text = (update.message.text or "").strip()
        if not text.startswith("#"):
            text = f"#{text}"
        ticket = db.get_ticket_by_code(text)
        if not ticket:
            await update.message.reply_text(
                f"❌ No ticket with code {text}.",
                reply_markup=admin_panel_keyboard(),
            )
            return ConversationHandler.END
        await update.message.reply_text(
            format_ticket_full(ticket),
            reply_markup=ticket_actions_keyboard(ticket["ticket_code"]),
        )
        return ConversationHandler.END
    except Exception:
        logger.exception("search_query error")
        return ConversationHandler.END


async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Start broadcast flow."""
    query = update.callback_query
    await query.answer()
    if not _require_admin(update):
        return ConversationHandler.END
    try:
        await query.edit_message_text(
            f"{brand_header()}\n\n📢 *Broadcast*\n\n"
            "Send the message you want to broadcast to all users (or /cancel).",
            parse_mode="Markdown",
        )
        return ADMIN_BROADCAST
    except Exception:
        logger.exception("broadcast_start error")
        return ConversationHandler.END


async def broadcast_preview(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Preview broadcast for confirmation."""
    if not _require_admin(update):
        return ConversationHandler.END
    try:
        ok, result = validate_message(update.message.text or "", min_len=1, max_len=3000)
        if not ok:
            await update.message.reply_text(f"❌ {result}")
            return ADMIN_BROADCAST
        context.user_data["broadcast_text"] = result
        await update.message.reply_text(
            f"📢 *Broadcast Preview*\n\n{result}\n\nSend to all users?",
            parse_mode="Markdown",
            reply_markup=broadcast_confirm_keyboard(),
        )
        return ConversationHandler.END
    except Exception:
        logger.exception("broadcast_preview error")
        return ConversationHandler.END


async def broadcast_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the broadcast."""
    query = update.callback_query
    await query.answer()
    if not _require_admin(update):
        return
    try:
        text = context.user_data.pop("broadcast_text", None)
        if not text:
            await query.edit_message_text("❌ No broadcast text.")
            return
        user_ids = db.get_all_user_ids()
        total = len(user_ids)
        sent = 0
        for i, uid in enumerate(user_ids, 1):
            ok = await safe_send(context.bot, uid, f"📢 {text}")
            if ok:
                sent += 1
            if i % 20 == 0:
                try:
                    await query.edit_message_text(f"📤 Sending... {sent}/{total}")
                except Exception:
                    pass
            await asyncio.sleep(0.05)  # rate-limit friendliness
        await query.edit_message_text(
            f"✅ Broadcast finished.\n\nDelivered: {sent}/{total}",
            reply_markup=admin_panel_keyboard(),
        )
    except Exception:
        logger.exception("broadcast_confirm error")


async def add_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Owner-only: add admin."""
    user = update.effective_user
    if not user or user.id != OWNER_ID:
        await update.message.reply_text("❌ Only the owner can do this.")
        return
    try:
        args = context.args or []
        if not args or not args[0].isdigit():
            await update.message.reply_text("Usage: /addadmin <user_id>")
            return
        new_id = int(args[0])
        db.add_admin(new_id, user.id)
        await update.message.reply_text(f"✅ Admin {new_id} added.")
        await safe_send(context.bot, new_id, f"🎉 You've been added as an admin of {BRAND_NAME}.")
    except Exception:
        logger.exception("add_admin error")


async def rm_admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Owner-only: remove admin."""
    user = update.effective_user
    if not user or user.id != OWNER_ID:
        await update.message.reply_text("❌ Only the owner can do this.")
        return
    try:
        args = context.args or []
        if not args or not args[0].isdigit():
            await update.message.reply_text("Usage: /rmadmin <user_id>")
            return
        target = int(args[0])
        if target == OWNER_ID:
            await update.message.reply_text("❌ Cannot remove owner.")
            return
        db.remove_admin(target)
        await update.message.reply_text(f"✅ Admin {target} removed.")
    except Exception:
        logger.exception("rm_admin error")


async def list_admins_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all admins."""
    if not _require_admin(update):
        await update.message.reply_text("❌ Unauthorized.")
        return
    try:
        ids = db.get_admins()
        lines = [f"{brand_header()}\n\n👥 *Admins ({len(ids)})*\n"]
        for i, aid in enumerate(ids, 1):
            tag = " 👑 (owner)" if aid == OWNER_ID else ""
            lines.append(f"{i}. `{aid}`{tag}")
        await update.message.reply_text(
            "\n".join(lines), parse_mode="Markdown"
        )
    except Exception:
        logger.exception("list_admins error")


async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Return to admin panel."""
    await admin_entry(update, context)


async def cancel_admin_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancel any admin conversation."""
    for key in ("admin_reply_ticket", "close_ticket", "broadcast_text"):
        context.user_data.pop(key, None)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            "❌ Cancelled.", reply_markup=admin_panel_keyboard()
        )
    else:
        await update.message.reply_text(
            "❌ Cancelled.", reply_markup=admin_panel_keyboard()
        )
    return ConversationHandler.END
