"""Scheduled task script for PythonAnywhere.

Set this up as a scheduled task on PythonAnywhere to run hourly:
    /home/YOUR_USERNAME/.virtualenvs/calendar-sync/bin/python /home/YOUR_USERNAME/calendar-sync/scheduled_check.py

This replaces the APScheduler background job when running on PythonAnywhere,
since PythonAnywhere free tier doesn't support always-on background workers.
"""

import os
import sys

# Add project directory to path
project_dir = os.path.dirname(os.path.abspath(__file__))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from app import check_new_events
from database import init_db

if __name__ == "__main__":
    init_db()
    results = check_new_events()
    print(
        f"Check complete: {results['events_found']} events found, "
        f"{results['prompts_created']} new prompts created."
    )
