"""SQLite database operations for the support bot."""

import logging
import sqlite3
import time
from datetime import datetime, timezone
from typing import Callable, Optional

from config import ADMINS, DB_PATH, OWNER_ID

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 0.5


def _utc_now() -> str:
    """Current UTC time as an ISO string (same format as before, no tz suffix)."""
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


def _utc_today() -> str:
    """Today's date in UTC (YYYY-MM-DD). Matches how created_at is stored."""
    return datetime.now(timezone.utc).date().isoformat()


def _get_connection() -> sqlite3.Connection:
    """Create a new SQLite connection with row factory."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _run_with_retry(work: Callable[[sqlite3.Connection], object]):
    """Run work(conn) in one transaction, retrying on 'database is locked'."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            conn = _get_connection()
            try:
                result = work(conn)
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


def _execute_with_retry(query: str, params: tuple = (), fetch: str = "none"):
    """Execute one query. fetch: 'one', 'all', 'rowcount' or 'none' (returns lastrowid)."""

    def work(conn: sqlite3.Connection):
        cur = conn.execute(query, params)
        if fetch == "one":
            return cur.fetchone()
        if fetch == "all":
            return cur.fetchall()
        if fetch == "rowcount":
            return cur.rowcount
        return cur.lastrowid

    return _run_with_retry(work)


def init_db() -> None:
    """Create all tables on first run."""
    conn = _get_connection()
    try:
        # WAL lets reads and writes happen together, so far fewer "database is locked" errors
        conn.execute("PRAGMA journal_mode=WAL")
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
            CREATE INDEX IF NOT EXISTS idx_tickets_user ON tickets(user_id);
            CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
            CREATE INDEX IF NOT EXISTS idx_messages_ticket ON messages(ticket_id);
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
        (user_id, username, first_name, _utc_now()),
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
    """Create a new ticket and return its code.

    The insert and the code assignment happen in ONE transaction, so two users
    creating tickets at the same moment can never get the same code.
    """

    def work(conn: sqlite3.Connection) -> str:
        cur = conn.execute(
            """INSERT INTO tickets (ticket_code, user_id, category, subject, message, status, created_at)
               VALUES (NULL, ?, ?, ?, ?, 'open', ?)""",
            (user_id, category, subject, message, _utc_now()),
        )
        code = f"#UPH-{cur.lastrowid:04d}"
        conn.execute("UPDATE tickets SET ticket_code = ? WHERE id = ?", (code, cur.lastrowid))
        return code

    ticket_code = _run_with_retry(work)
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
    """Close a ticket. Returns True only if this call actually closed it."""
    changed = _execute_with_retry(
        """UPDATE tickets SET status='closed', closed_at=?, closed_reason=?
           WHERE ticket_code=? AND status='open'""",
        (_utc_now(), reason, ticket_code),
        fetch="rowcount",
    )
    return changed > 0


def add_message(ticket_id: int, sender_id: int, sender_type: str, text: str) -> None:
    """Append a message to a ticket thread."""
    _execute_with_retry(
        """INSERT INTO messages (ticket_id, sender_id, sender_type, message_text, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (ticket_id, sender_id, sender_type, text, _utc_now()),
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
        (user_id, added_by, _utc_now()),
    )


def remove_admin(user_id: int) -> None:
    """Remove an admin."""
    _execute_with_retry("DELETE FROM admins WHERE user_id = ?", (user_id,))


def get_admins() -> list[int]:
    """Return all admin user IDs (DB + env config)."""
    rows = _execute_with_retry("SELECT user_id FROM admins", fetch="all")
    combined = {row["user_id"] for row in rows}
    combined.update(ADMINS)
    if OWNER_ID:
        combined.add(OWNER_ID)
    return sorted(combined)


def is_admin(user_id: int) -> bool:
    """Check if a user is an admin or owner."""
    if user_id == OWNER_ID or user_id in ADMINS:
        return True
    row = _execute_with_retry(
        "SELECT 1 FROM admins WHERE user_id = ?", (user_id,), fetch="one"
    )
    return row is not None


def get_stats() -> dict:
    """Return statistics about tickets."""
    today = _utc_today()

    def work(conn: sqlite3.Connection) -> dict:
        total = conn.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        open_count = conn.execute(
            "SELECT COUNT(*) FROM tickets WHERE status='open'"
        ).fetchone()[0]
        today_count = conn.execute(
            "SELECT COUNT(*) FROM tickets WHERE created_at LIKE ?", (f"{today}%",)
        ).fetchone()[0]
        users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        return {
            "total": total,
            "open": open_count,
            "closed": total - open_count,
            "today": today_count,
            "users": users,
        }

    return _run_with_retry(work)


def user_tickets_today(user_id: int) -> int:
    """Count how many tickets a user created today (UTC)."""
    row = _execute_with_retry(
        "SELECT COUNT(*) AS c FROM tickets WHERE user_id=? AND created_at LIKE ?",
        (user_id, f"{_utc_today()}%"),
        fetch="one",
    )
    return row["c"] if row else 0
