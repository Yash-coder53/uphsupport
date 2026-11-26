"""Inline and reply keyboard builders."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from config import CATEGORIES, FAQ_ITEMS


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """Main menu for regular users."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📖 FAQ", callback_data="faq_0")],
            [InlineKeyboardButton("🎫 Create Support Ticket", callback_data="ticket_new")],
            [InlineKeyboardButton("📋 My Tickets", callback_data="my_tickets")],
            [InlineKeyboardButton("ℹ️ About Us", callback_data="about")],
            [InlineKeyboardButton("📞 Contact Admin", callback_data="contact_admin")],
        ]
    )


def faq_keyboard(index: int) -> InlineKeyboardMarkup:
    """Navigation for FAQ items."""
    total = len(FAQ_ITEMS)
    nav_row = []
    if index > 0:
        nav_row.append(InlineKeyboardButton("⬅️ Back", callback_data=f"faq_{index - 1}"))
    if index < total - 1:
        nav_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"faq_{index + 1}"))
    rows = [[InlineKeyboardButton(f"{index + 1}/{total}", callback_data="noop")]]
    if nav_row:
        rows.append(nav_row)
    rows.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


def category_keyboard() -> InlineKeyboardMarkup:
    """Ticket category selection."""
    rows = [[InlineKeyboardButton(label, callback_data=f"cat_{key}")] for key, label in CATEGORIES]
    rows.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel_ticket")])
    return InlineKeyboardMarkup(rows)


def confirm_ticket_keyboard() -> InlineKeyboardMarkup:
    """Confirm or cancel ticket submission."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Submit Ticket", callback_data="ticket_submit")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_ticket")],
        ]
    )


def skip_attachment_keyboard() -> InlineKeyboardMarkup:
    """Skip attachment option."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("⏭️ Skip", callback_data="skip_attachment")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel_ticket")],
        ]
    )


def back_to_menu_keyboard() -> InlineKeyboardMarkup:
    """Simple back-to-menu button."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")]]
    )


def ticket_actions_keyboard(ticket_code: str) -> InlineKeyboardMarkup:
    """Admin actions on a ticket notification."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💬 Reply", callback_data=f"admin_reply_{ticket_code}")],
            [InlineKeyboardButton("✅ Close", callback_data=f"admin_close_{ticket_code}")],
            [InlineKeyboardButton("👤 View User", callback_data=f"admin_view_{ticket_code}")],
        ]
    )


def user_reply_back_keyboard(ticket_code: str) -> InlineKeyboardMarkup:
    """User reply-back button after admin reply."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("💬 Reply Back", callback_data=f"user_reply_{ticket_code}")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
        ]
    )


def my_tickets_keyboard(tickets) -> InlineKeyboardMarkup:
    """List tickets with reply buttons for open ones."""
    rows = []
    for t in tickets:
        icon = "🟢" if t["status"] == "open" else "🔴"
        rows.append(
            [
                InlineKeyboardButton(
                    f"{icon} {t['ticket_code']} — {t['subject']}",
                    callback_data=f"view_ticket_{t['ticket_code']}",
                )
            ]
        )
    rows.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


def ticket_detail_keyboard(ticket_code: str, is_open: bool) -> InlineKeyboardMarkup:
    """Detail view for a ticket."""
    rows = []
    if is_open:
        rows.append(
            [InlineKeyboardButton("💬 Reply", callback_data=f"user_reply_{ticket_code}")]
        )
    rows.append([InlineKeyboardButton("⬅️ Back to My Tickets", callback_data="my_tickets")])
    rows.append([InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


def admin_panel_keyboard() -> InlineKeyboardMarkup:
    """Admin panel buttons."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
            [InlineKeyboardButton("🎫 Open Tickets", callback_data="admin_open_tickets_0")],
            [InlineKeyboardButton("🔍 Search Ticket by ID", callback_data="admin_search")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🏠 Main Menu", callback_data="main_menu")],
        ]
    )


def pagination_keyboard(prefix: str, page: int, has_next: bool) -> InlineKeyboardMarkup:
    """Generic pagination controls."""
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"{prefix}{page - 1}"))
    if has_next:
        nav.append(InlineKeyboardButton("Next ➡️", callback_data=f"{prefix}{page + 1}"))
    rows = []
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("⬅️ Admin Panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(rows)


def close_confirm_keyboard(ticket_code: str) -> InlineKeyboardMarkup:
    """Confirm closing a ticket."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Close without reason", callback_data=f"close_now_{ticket_code}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")],
        ]
    )


def broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    """Confirm broadcast."""
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Send Broadcast", callback_data="broadcast_confirm")],
            [InlineKeyboardButton("❌ Cancel", callback_data="admin_panel")],
        ]
      )
