"""Full sync script — process ALL existing calendar events, not just recent ones.

Run on PythonAnywhere:
    cd ~/calendar-sync && python full_sync.py

This resets the last-check timestamps and clears previously processed events
so that check_new_events() picks up everything from the past N days.
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone

# Add project directory to path
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

import database as db
from app import check_new_events


def full_sync(lookback_days: int = 365) -> None:
    """Reset state and re-process all events from the past lookback_days."""
    db.init_db()

    # Calculate how far back to look
    since = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    since_str = since.isoformat()

    print(f"Full sync: looking back {lookback_days} days (since {since.date()})")

    # Reset last check times so check_new_events() looks back far enough
    conn = db.get_connection()
    try:
        conn.execute("DELETE FROM app_state WHERE key LIKE 'last_check_%'")
        # Clear processed events so they get re-evaluated
        conn.execute("DELETE FROM processed_events")
        conn.commit()
        print("Cleared last-check timestamps and processed events table.")
    finally:
        conn.close()

    # Temporarily override INITIAL_LOOKBACK_HOURS so the lookback covers our range
    import config
    original_lookback = config.INITIAL_LOOKBACK_HOURS
    config.INITIAL_LOOKBACK_HOURS = lookback_days * 24

    try:
        results = check_new_events()
        print(
            f"\nFull sync complete!\n"
            f"  Events found: {results['events_found']}\n"
            f"  Prompts created: {results['prompts_created']}\n"
            f"\nCheck your dashboard to review the prompts."
        )
    finally:
        config.INITIAL_LOOKBACK_HOURS = original_lookback


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Full calendar sync — process all existing events")
    parser.add_argument(
        "--days",
        type=int,
        default=365,
        help="How many days back to look (default: 365)",
    )
    args = parser.parse_args()
    full_sync(args.days)
