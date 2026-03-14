"""Google Calendar read/write operations."""

from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google.cloud import firestore
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from config import GCP_PROJECT_ID, SCOPES, USERS


def _get_credentials(user_id: str) -> Credentials:
    """Load OAuth credentials for a user from Firestore."""
    db = firestore.Client(project=GCP_PROJECT_ID)
    doc = db.collection("user_tokens").document(user_id).get()
    if not doc.exists:
        raise ValueError(
            f"No stored credentials for {user_id}. Run setup_auth.py first."
        )

    data = doc.to_dict()
    creds = Credentials(
        token=data["token"],
        refresh_token=data["refresh_token"],
        token_uri=data["token_uri"],
        client_id=data["client_id"],
        client_secret=data["client_secret"],
        scopes=SCOPES,
    )

    # Refresh if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        # Update stored token
        db.collection("user_tokens").document(user_id).update({
            "token": creds.token,
        })

    return creds


def _get_service(user_id: str):
    """Build a Google Calendar API service for a user."""
    creds = _get_credentials(user_id)
    return build("calendar", "v3", credentials=creds)


def get_calendar_list(user_id: str) -> list[dict]:
    """List all calendars for a user."""
    service = _get_service(user_id)
    result = service.calendarList().list().execute()
    calendars = result.get("items", [])
    # Only return calendars the user owns (skip subscribed read-only ones
    # like holidays, unless they have write access)
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
    """Fetch events created or modified since the given timestamp.

    If calendar_ids is None, fetches from all owned calendars.
    """
    service = _get_service(user_id)

    if calendar_ids is None:
        calendars = get_calendar_list(user_id)
        calendar_ids = [cal["id"] for cal in calendars]

    since_rfc = since.astimezone(timezone.utc).isoformat()
    events = []

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
            # Skip calendars that error (e.g., permissions issues)
            continue

        cal_name = cal_id  # Default to ID
        for cal in get_calendar_list(user_id):
            if cal["id"] == cal_id:
                cal_name = cal["summary"]
                break

        for event in result.get("items", []):
            # Skip cancelled events
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
    """Create a notification event on the creator's primary calendar
    and invite the other person.

    Args:
        creator_user_id: The user creating the event (e.g., "alex")
        summary: Event title (e.g., "Alex at movie (Alamo Drafthouse)")
        start_time: ISO 8601 datetime string
        end_time: ISO 8601 datetime string
        invitee_email: Email to invite (the partner)

    Returns:
        The created event resource.
    """
    service = _get_service(creator_user_id)

    # Determine if this is an all-day event (date only, no time component)
    is_all_day = len(start_time) <= 10  # "2026-03-18" vs "2026-03-18T18:00:00-05:00"

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
        # Send email notification to the invitee
        "reminders": {"useDefault": True},
    }

    created = (
        service.events()
        .insert(
            calendarId="primary",
            body=event_body,
            sendUpdates="all",  # Sends invite email to attendees
        )
        .execute()
    )

    return created
