"""Configuration for the Calendar Sync app."""

import os

from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

# Base directory (where this file lives)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# SQLite database path
DATABASE_PATH = os.environ.get(
    "DATABASE_PATH", os.path.join(BASE_DIR, "calendar_sync.db")
)

# Google Calendar OAuth credentials file (downloaded from GCP console)
GOOGLE_CREDENTIALS_FILE = os.environ.get(
    "GOOGLE_CREDENTIALS_FILE", os.path.join(BASE_DIR, "credentials.json")
)

# Directory to store OAuth tokens locally
TOKEN_DIR = os.environ.get(
    "TOKEN_DIR", os.path.join(BASE_DIR, "tokens")
)

# Flask secret key (for session security)
SECRET_KEY = os.environ.get("SECRET_KEY", "change-me-in-production")

# Flask host/port
HOST = os.environ.get("HOST", "127.0.0.1")
PORT = int(os.environ.get("PORT", "5000"))

# How often to check calendars (in minutes)
CHECK_INTERVAL_MINUTES = int(os.environ.get("CHECK_INTERVAL_MINUTES", "60"))

# How far back to look for events on first run (in hours)
INITIAL_LOOKBACK_HOURS = int(os.environ.get("INITIAL_LOOKBACK_HOURS", "24"))

# User configuration
USERS = {
    "alex": {
        "email": os.environ.get("ALEX_EMAIL", ""),
        "phone": os.environ.get("ALEX_PHONE", ""),
        "partner": "sara",
    },
    "sara": {
        "email": os.environ.get("SARA_EMAIL", "annear.sara@gmail.com"),
        "phone": os.environ.get("SARA_PHONE", ""),
        "partner": "alex",
    },
}

# Google Calendar OAuth scopes
SCOPES = ["https://www.googleapis.com/auth/calendar"]
