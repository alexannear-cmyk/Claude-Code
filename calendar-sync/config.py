"""Configuration for the Calendar Sync app."""

import os


# Google Calendar OAuth
GOOGLE_CREDENTIALS_FILE = os.environ.get(
    "GOOGLE_CREDENTIALS_FILE", "credentials.json"
)

# Anthropic
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Twilio
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN", "")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER", "")

# Google Cloud project (for Firestore)
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "")

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

# How far back to look for events on first run (in hours)
INITIAL_LOOKBACK_HOURS = 24

# Calendar scopes
SCOPES = ["https://www.googleapis.com/auth/calendar"]
