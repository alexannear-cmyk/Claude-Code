"""Google Calendar read/write operations."""

import json
import os
import time
from datetime import datetime, timezone

import requests as http_requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config import GOOGLE_CREDENTIALS_FILE, SCOPES, TOKEN_DIR, USERS


def _get_token_path(user_id: str) -> str:
    """Get the path to a user's token file."""
    os.makedirs(TOKEN_DIR, exist_ok=True)
    return os.path.join(TOKEN_DIR, f"{user_id}_token.json")


def _get_credentials(user_id: str) -> Credentials:
    """Load OAuth credentials for a user from local token file."""
    token_path = _get_token_path(user_id)

    if not os.path.exists(token_path):
        raise ValueError(
            f"No stored credentials for {user_id}. Run setup_auth.py first."
        )

    creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    # Refresh if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Save refreshed token
        with open(token_path, "w") as f:
            f.write(creds.to_json())

    return creds


def authorize_user(user_id: str) -> None:
    """Run OAuth authorization for a user using google_auth_oauthlib.

    Starts a local HTTP server to receive the OAuth callback.
    Run this on a machine with a browser.
    """
    from google_auth_oauthlib.flow import InstalledAppFlow

    if user_id not in USERS:
        raise ValueError(f"Unknown user: {user_id}. Must be one of: {list(USERS.keys())}")

    print(f"Authorizing {user_id} ({USERS[user_id]['email']})...")

    flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=8080, prompt="consent", access_type="offline")

    token_path = _get_token_path(user_id)
    with open(token_path, "w") as f:
        f.write(creds.to_json())

    print(f"Successfully authorized {user_id}! Token saved to {token_path}")


def _get_service(user_id: str):
    """Build a Google Calendar API service for a user."""
    creds = _get_credentials(user_id)
    return build("calendar", "v3", credentials=creds)


def get_calendar_list(user_id: str) -> list[dict]:
    """List all calendars the user owns or can write to."""
    service = _get_service(user_id)
    result = service.calendarList().list().execute()
    calendars = result.get("items", [])
    return [
        {
            "id": cal["id"],
            "summary": cal.get("summary", "(no title)"),
            "primary": cal.get("primary", False),
            "access_role": cal.get("accessRole", "reader"),
        }
        for cal in calendars
        if cal.get("accessRole") in ("owner", "writer")
    ]


def get_recent_events(
    user_id: str, since: datetime, calendar_ids: list[str] | None = None
) -> list[dict]:
    """Fetch events created or modified since the given timestamp."""
    service = _get_service(user_id)

    if calendar_ids is None:
        calendars = get_calendar_list(user_id)
        calendar_ids = [cal["id"] for cal in calendars]

    since_rfc = since.astimezone(timezone.utc).isoformat()
    events = []

    # Build a calendar ID -> name mapping in one pass
    all_calendars = get_calendar_list(user_id)
    cal_names = {cal["id"]: cal["summary"] for cal in all_calendars}

    for cal_id in calendar_ids:
        try:
            result = (
                service.events()
                .list(
                    calendarId=cal_id,
                    updatedMin=since_rfc,
                    singleEvents=True,
                    orderBy="updated",
                    maxResults=50,
                )
                .execute()
            )
        except Exception:
            continue

        cal_name = cal_names.get(cal_id, cal_id)

        for event in result.get("items", []):
            if event.get("status") == "cancelled":
                continue

            start = event.get("start", {})
            end = event.get("end", {})

            events.append({
                "id": event["id"],
                "calendar_id": cal_id,
                "calendar_name": cal_name,
                "summary": event.get("summary", "(no title)"),
                "description": event.get("description", ""),
                "location": event.get("location", ""),
                "start": start.get("dateTime", start.get("date", "")),
                "end": end.get("dateTime", end.get("date", "")),
                "all_day": "date" in start and "dateTime" not in start,
                "creator_email": event.get("creator", {}).get("email", ""),
                "updated": event.get("updated", ""),
            })

    return events


def create_notification_event(
    creator_user_id: str,
    summary: str,
    start_time: str,
    end_time: str,
    invitee_email: str,
) -> dict:
    """Create a notification event and invite the partner.

    Args:
        creator_user_id: The user creating the event (e.g., "alex")
        summary: Event title (e.g., "Alex at movie (Alamo Drafthouse)")
        start_time: ISO 8601 datetime or date string
        end_time: ISO 8601 datetime or date string
        invitee_email: Email to invite (the partner)

    Returns:
        The created event resource.
    """
    service = _get_service(creator_user_id)

    is_all_day = len(start_time) <= 10

    if is_all_day:
        start_body = {"date": start_time}
        end_body = {"date": end_time}
    else:
        start_body = {"dateTime": start_time}
        end_body = {"dateTime": end_time}

    event_body = {
        "summary": summary,
        "start": start_body,
        "end": end_body,
        "attendees": [{"email": invitee_email}],
        "reminders": {"useDefault": True},
    }

    created = (
        service.events()
        .insert(
            calendarId="primary",
            body=event_body,
            sendUpdates="all",
        )
        .execute()
    )

    return created
