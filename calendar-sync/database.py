"""SQLite database operations for Calendar Sync."""

import sqlite3
from datetime import datetime, timezone


def _default_db_path() -> str:
    """Get the database path from config at call time (not import time)."""
    from config import DATABASE_PATH
    return DATABASE_PATH


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    """Get a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(db_path or _default_db_path())
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db(db_path: str | None = None) -> None:
    """Create tables if they don't exist."""
    conn = get_connection(db_path)
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS processed_events (
                event_id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                action TEXT NOT NULL,
                processed_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS pending_prompts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                partner_id TEXT NOT NULL,
                event_id TEXT NOT NULL,
                event_summary TEXT NOT NULL,
                event_start TEXT NOT NULL,
                event_end TEXT NOT NULL,
                event_all_day INTEGER NOT NULL DEFAULT 0,
                suggested_summary TEXT NOT NULL,
                partner_email TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS app_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        conn.commit()
    finally:
        conn.close()


def is_event_processed(event_id: str, db_path: str | None = None) -> bool:
    """Check if an event has already been processed."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT 1 FROM processed_events WHERE event_id = ?", (event_id,)
        ).fetchone()
        return row is not None
    finally:
        conn.close()


def mark_event_processed(
    event_id: str, user_id: str, action: str, db_path: str | None = None
) -> None:
    """Mark an event as processed."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO processed_events (event_id, user_id, action, processed_at) "
            "VALUES (?, ?, ?, ?)",
            (event_id, user_id, action, datetime.now(timezone.utc).isoformat()),
        )
        conn.commit()
    finally:
        conn.close()


def store_pending_prompt(
    user_id: str,
    partner_id: str,
    event_id: str,
    event_summary: str,
    event_start: str,
    event_end: str,
    event_all_day: bool,
    suggested_summary: str,
    partner_email: str,
    db_path: str | None = None,
) -> int:
    """Store a pending prompt and return its ID."""
    conn = get_connection(db_path)
    try:
        cursor = conn.execute(
            "INSERT INTO pending_prompts "
            "(user_id, partner_id, event_id, event_summary, event_start, "
            "event_end, event_all_day, suggested_summary, partner_email, "
            "status, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)",
            (
                user_id,
                partner_id,
                event_id,
                event_summary,
                event_start,
                event_end,
                int(event_all_day),
                suggested_summary,
                partner_email,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_pending_prompts(
    user_id: str | None = None, db_path: str | None = None
) -> list[dict]:
    """Get all pending prompts, optionally filtered by user."""
    conn = get_connection(db_path)
    try:
        if user_id:
            rows = conn.execute(
                "SELECT * FROM pending_prompts WHERE status = 'pending' "
                "AND user_id = ? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM pending_prompts WHERE status = 'pending' "
                "ORDER BY created_at DESC"
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def update_prompt_status(
    prompt_id: int, status: str, db_path: str | None = None
) -> None:
    """Update a prompt's status (pending, accepted, dismissed)."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            "UPDATE pending_prompts SET status = ? WHERE id = ?",
            (status, prompt_id),
        )
        conn.commit()
    finally:
        conn.close()


def get_prompt_by_id(
    prompt_id: int, db_path: str | None = None
) -> dict | None:
    """Get a specific prompt by ID."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT * FROM pending_prompts WHERE id = ?", (prompt_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_last_check_time(
    user_id: str, db_path: str | None = None
) -> str | None:
    """Get the last time we checked a user's calendar."""
    conn = get_connection(db_path)
    try:
        row = conn.execute(
            "SELECT value FROM app_state WHERE key = ?",
            (f"last_check_{user_id}",),
        ).fetchone()
        return row["value"] if row else None
    finally:
        conn.close()


def set_last_check_time(
    user_id: str, timestamp: str, db_path: str | None = None
) -> None:
    """Set the last check timestamp for a user."""
    conn = get_connection(db_path)
    try:
        conn.execute(
            "INSERT OR REPLACE INTO app_state (key, value) VALUES (?, ?)",
            (f"last_check_{user_id}", timestamp),
        )
        conn.commit()
    finally:
        conn.close()


def get_recent_history(
    limit: int = 20, db_path: str | None = None
) -> list[dict]:
    """Get recent prompt history (all statuses) for the dashboard."""
    conn = get_connection(db_path)
    try:
        rows = conn.execute(
            "SELECT * FROM pending_prompts ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()
