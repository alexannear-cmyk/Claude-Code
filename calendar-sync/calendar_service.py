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


def _run_callback_server(port: int, result: dict) -> None:
    """Run a temporary HTTP server to capture the OAuth callback."""
    import http.server

    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            from urllib.parse import parse_qs, urlparse
            query = parse_qs(urlparse(self.path).query)
            if "code" in query:
                result["code"] = query["code"][0]
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<h2>Authorization successful!</h2>"
                    b"<p>You can close this tab and return to the terminal.</p>"
                )
            else:
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h2>Authorization failed</h2><p>No code received.</p>")

        def log_message(self, format, *args):
            pass  # Suppress server logs

    server = http.server.HTTPServer(("127.0.0.1", port), CallbackHandler)
    server.timeout = 300  # 5-minute timeout
    server.handle_request()
    server.server_close()


def authorize_user(user_id: str) -> None:
    """Run OAuth authorization for a user.

    Starts a temporary local server to capture the OAuth callback automatically
    when using a desktop browser. For mobile browsers, falls back to manual
    code copying from the URL bar.
    """
    import threading

    if user_id not in USERS:
        raise ValueError(f"Unknown user: {user_id}. Must be one of: {list(USERS.keys())}")

    with open(GOOGLE_CREDENTIALS_FILE) as f:
        cred_data = json.load(f)

    client_info = cred_data.get("installed") or cred_data.get("web")
    if not client_info:
        raise ValueError("Invalid credentials.json format")

    client_id = client_info["client_id"]
    client_secret = client_info["client_secret"]

    # Try to start a local callback server
    callback_port = 8085
    callback_result = {}
    try:
        server_thread = threading.Thread(
            target=_run_callback_server, args=(callback_port, callback_result), daemon=True
        )
        server_thread.start()
        redirect_uri = f"http://localhost:{callback_port}"
        server_running = True
    except OSError:
        redirect_uri = "http://localhost:1"
        server_running = False

    auth_url = (
        "https://accounts.google.com/o/oauth2/v2/auth"
        f"?client_id={client_id}"
        f"&redirect_uri={redirect_uri}"
        "&response_type=code"
        f"&scope={'+'.join(SCOPES)}"
        "&access_type=offline"
        "&prompt=consent"
    )

    print(f"\nAuthorizing {user_id} ({USERS[user_id]['email']})...\n")
    print("=" * 60)
    print("1. Open this URL in a browser on THIS COMPUTER:\n")
    print(f"   {auth_url}\n")
    print(f"2. Sign in with: {USERS[user_id]['email']}")
    print("3. Click 'Allow' to grant calendar access")
    if server_running:
        print("4. The browser will show 'Authorization successful!'")
        print("   and the token will be saved automatically.")
        print()
        print("--- ON A PHONE? ---")
        print("The auto-capture won't work from a phone browser.")
        print("After clicking Allow, the page will spin. That's OK!")
        print("Tap the URL/address bar, copy the full URL, and look for")
        print("the code between 'code=' and '&scope' — paste it below.")
    else:
        print("4. The page will fail to load — that's OK!")
        print("5. Look at the URL bar. It will look like:")
        print(f"   {redirect_uri}/?code=XXXXX&scope=...")
        print("6. Copy everything between 'code=' and '&scope'")
        print("   and paste it below")
    print("=" * 60)

    if server_running:
        print("\nWaiting for callback (or paste the code manually)...")
        # Wait for server callback or manual input
        import select
        import sys

        server_thread.join(timeout=1)
        while server_thread.is_alive() and "code" not in callback_result:
            # Check for manual input (non-blocking)
            if select.select([sys.stdin], [], [], 1)[0]:
                manual_code = sys.stdin.readline().strip()
                if manual_code:
                    callback_result["code"] = manual_code
                    break

        if "code" not in callback_result:
            # Server timed out
            manual_code = input("\nAuto-capture timed out. Paste the code here: ").strip()
            callback_result["code"] = manual_code

        auth_code = callback_result["code"]
    else:
        auth_code = input("\nPaste the code here: ").strip()

    token_resp = http_requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "client_id": client_id,
            "client_secret": client_secret,
            "code": auth_code,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
        },
    )

    if token_resp.status_code != 200:
        raise RuntimeError(f"Token exchange failed: {token_resp.json()}")

    token_data = token_resp.json()

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

    print(f"\nSuccessfully authorized {user_id}! Token saved to {token_path}")


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
