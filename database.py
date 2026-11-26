"""SQLite database operations for the support bot."""

import sqlite3
import time
import logging
from datetime import datetime, date
from typing import Optional

from config import DB_PATH

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 0.5


def _get_connection() -> sqlite3.Connection:
    """Create a new SQLite connection with row factory."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _execute_with_retry(query: str, params: tuple = (), fetch: str = "none"):
    """Execute a query with retry logic for 'database is locked' errors."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            conn = _get_connection()
            try:
                cur = conn.execute(query, params)
                if fetch == "one":
                    result = cur.fetchone()
                elif fetch == "all":
                    result = cur.fetchall()
                else:
                    result = cur.lastrowid
                conn.commit()
                return result
            finally:
                conn.close()
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < MAX_RETRIES:
                logger.warning("DB locked, retry %d/%d", attempt, MAX_RETRIES)
                time.sleep(RETRY_DELAY)
            else:
                raise


def init_db() -> None:
    """Create all tables on first run."""
    conn = _get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                joined_at TEXT
            );
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_code TEXT UNIQUE,
                user_id INTEGER,
                category TEXT,
                subject TEXT,
                message TEXT,
                status TEXT DEFAULT 'open',
                created_at TEXT,
                closed_at TEXT,
                closed_reason TEXT
            );
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id INTEGER,
                sender_id INTEGER,
                sender_type TEXT,
                message_text TEXT,
                created_at TEXT
            );
            CREATE TABLE IF NOT EXISTS admins (
                user_id INTEGER PRIMARY KEY,
                added_by INTEGER,
                added_at TEXT
            );
            """
        )
        conn.commit()
        logger.info("Database initialized")
    finally:
        conn.close()


def upsert_user(user_id: int, username: Optional[str], first_name: Optional[str]) -> None:
    """Insert or update a user record."""
    _execute_with_retry(
        """INSERT INTO users (user_id, username, first_name, joined_at)
           VALUES (?, ?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET
             username=excluded.username, first_name=excluded.first_name""",
        (user_id, username, first_name, datetime.utcnow().isoformat()),
    )


def get_user(user_id: int) -> Optional[sqlite3.Row]:
    """Fetch a user by ID."""
    return _execute_with_retry(
        "SELECT * FROM users WHERE user_id = ?", (user_id,), fetch="one"
    )


def get_all_user_ids() -> list[int]:
    """Return all user IDs for broadcasting."""
    rows = _execute_with_retry("SELECT user_id FROM users", fetch="all")
    return [row["user_id"] for row in rows]


def create_ticket(user_id: int, category: str, subject: str, message: str) -> str:
    """Create a new ticket and return its code."""
    row = _execute_with_retry(
        "SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM tickets", fetch="one"
    )
    next_id = row["next_id"]
    ticket_code = f"#UPH-{next_id:04d}"
    _execute_with_retry(
        """INSERT INTO tickets (ticket_code, user_id, category, subject, message, status, created_at)
           VALUES (?, ?, ?, ?, ?, 'open', ?)""",
        (ticket_code, user_id, category, subject, message, datetime.utcnow().isoformat()),
    )
    logger.info("Ticket %s created for user %s", ticket_code, user_id)
    return ticket_code


def get_ticket_by_code(ticket_code: str) -> Optional[sqlite3.Row]:
    """Fetch a ticket by its code."""
    return _execute_with_retry(
        "SELECT * FROM tickets WHERE ticket_code = ?", (ticket_code,), fetch="one"
    )


def get_ticket_by_id(ticket_id: int) -> Optional[sqlite3.Row]:
    """Fetch a ticket by DB id."""
    return _execute_with_retry(
        "SELECT * FROM tickets WHERE id = ?", (ticket_id,), fetch="one"
    )


def get_user_tickets(user_id: int) -> list[sqlite3.Row]:
    """Return all tickets for a user, newest first."""
    return _execute_with_retry(
        "SELECT * FROM tickets WHERE user_id = ? ORDER BY id DESC",
        (user_id,),
        fetch="all",
    )


def get_open_tickets(limit: int = 50, offset: int = 0) -> list[sqlite3.Row]:
    """Return paginated open tickets."""
    return _execute_with_retry(
        "SELECT * FROM tickets WHERE status = 'open' ORDER BY id ASC LIMIT ? OFFSET ?",
        (limit, offset),
        fetch="all",
    )


def close_ticket(ticket_code: str, reason: str = "") -> bool:
    """Close a ticket. Returns True if updated."""
    row = get_ticket_by_code(ticket_code)
    if not row or row["status"] == "closed":
        return False
    _execute_with_retry(
        "UPDATE tickets SET status='closed', closed_at=?, closed_reason=? WHERE ticket_code=?",
        (datetime.utcnow().isoformat(), reason, ticket_code),
    )
    return True


def add_message(ticket_id: int, sender_id: int, sender_type: str, text: str) -> None:
    """Append a message to a ticket thread."""
    _execute_with_retry(
        """INSERT INTO messages (ticket_id, sender_id, sender_type, message_text, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (ticket_id, sender_id, sender_type, text, datetime.utcnow().isoformat()),
    )


def get_messages(ticket_id: int) -> list[sqlite3.Row]:
    """Fetch all messages for a ticket."""
    return _execute_with_retry(
        "SELECT * FROM messages WHERE ticket_id = ? ORDER BY id ASC",
        (ticket_id,),
        fetch="all",
    )


def add_admin(user_id: int, added_by: int) -> None:
    """Add an admin."""
    _execute_with_retry(
        "INSERT OR IGNORE INTO admins (user_id, added_by, added_at) VALUES (?, ?, ?)",
        (user_id, added_by, datetime.utcnow().isoformat()),
    )


def remove_admin(user_id: int) -> None:
    """Remove an admin."""
    _execute_with_retry("DELETE FROM admins WHERE user_id = ?", (user_id,))


def get_admins() -> list[int]:
    """Return all admin user IDs (DB + env config)."""
    rows = _execute_with_retry("SELECT user_id FROM admins", fetch="all")
    db_ids = [row["user_id"] for row in rows]
    combined = set(db_ids)
    from config import ADMINS, OWNER_ID
    combined.update(ADMINS)
    if OWNER_ID:
        combined.add(OWNER_ID)
    return sorted(combined)


def is_admin(user_id: int) -> bool:
    """Check if a user is an admin or owner."""
    from config import ADMINS, OWNER_ID
    if user_id == OWNER_ID or user_id in ADMINS:
        return True
    row = _execute_with_retry(
        "SELECT 1 FROM admins WHERE user_id = ?", (user_id,), fetch="one"
    )
    return row is not None


def get_stats() -> dict:
    """Return statistics about tickets."""
    total = _execute_with_retry("SELECT COUNT(*) AS c FROM tickets", fetch="one")["c"]
    open_count = _execute_with_retry(
        "SELECT COUNT(*) AS c FROM tickets WHERE status='open'", fetch="one"
    )["c"]
    closed = total - open_count
    today = date.today().isoformat()
    today_count = _execute_with_retry(
        "SELECT COUNT(*) AS c FROM tickets WHERE created_at LIKE ?",
        (f"{today}%",),
        fetch="one",
    )["c"]
    users = _execute_with_retry("SELECT COUNT(*) AS c FROM users", fetch="one")["c"]
    return {
        "total": total,
        "open": open_count,
        "closed": closed,
        "today": today_count,
        "users": users,
    }


def user_tickets_today(user_id: int) -> int:
    """Count how many tickets a user created today."""
    today = date.today().isoformat()
    row = _execute_with_retry(
        "SELECT COUNT(*) AS c FROM tickets WHERE user_id=? AND created_at LIKE ?",
        (user_id, f"{today}%"),
        fetch="one",
    )
    return row["c"] if row else 0
