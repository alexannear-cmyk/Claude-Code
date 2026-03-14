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
    """Run the OAuth Device Flow for a user and save the token locally.

    Works anywhere — PythonAnywhere, headless servers, etc.
    Prints a URL and code. Open the URL on any device (phone, laptop),
    enter the code, and sign in. The script waits automatically.
    """
    if user_id not in USERS:
        raise ValueError(f"Unknown user: {user_id}. Must be one of: {list(USERS.keys())}")

    # Load client credentials from the downloaded JSON
    with open(GOOGLE_CREDENTIALS_FILE) as f:
        cred_data = json.load(f)

    # Handle both "installed" and "web" credential types
    client_info = cred_data.get("installed") or cred_data.get("web")
    if not client_info:
        raise ValueError("Invalid credentials.json format")

    client_id = client_info["client_id"]
    client_secret = client_info["client_secret"]

    print(f"Authorizing {user_id} ({USERS[user_id]['email']})...")

    # Step 1: Request device code
    resp = http_requests.post(
        "https://oauth2.googleapis.com/device/code",
        data={
            "client_id": client_id,
            "scope": " ".join(SCOPES),
        },
    )
    resp.raise_for_status()
    device_data = resp.json()

    user_code = device_data["user_code"]
    verification_url = device_data["verification_url"]
    device_code = device_data["device_code"]
    interval = device_data.get("interval", 5)

    print()
    print("=" * 60)
    print(f"1. Open this URL on your phone or any browser:")
    print()
    print(f"   {verification_url}")
    print()
    print(f"2. Enter this code:  {user_code}")
    print()
    print(f"3. Sign in with: {USERS[user_id]['email']}")
    print("=" * 60)
    print()
    print("Waiting for you to approve...")

    # Step 2: Poll for authorization
    while True:
        time.sleep(interval)
        token_resp = http_requests.post(
            "https://oauth2.googleapis.com/token",
            data={
                "client_id": client_id,
                "client_secret": client_secret,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            },
        )
        token_data = token_resp.json()

        if "access_token" in token_data:
            break

        error = token_data.get("error")
        if error == "authorization_pending":
            continue
        elif error == "slow_down":
            interval += 2
            continue
        else:
            raise RuntimeError(f"Authorization failed: {token_data}")

    # Step 3: Save the token
    credentials = Credentials(
        token=token_data["access_token"],
        refresh_token=token_data.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )

    token_path = _get_token_path(user_id)
    with open(token_path, "w") as f:
        f.write(credentials.to_json())

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
