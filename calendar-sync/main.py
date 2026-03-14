"""Cloud Function entry points for Calendar Sync.

Two functions:
    - check_new_events: Triggered hourly by Cloud Scheduler. Scans calendars
      for new events, filters with AI, and sends SMS prompts.
    - handle_sms_reply: Triggered by Twilio webhook when a user replies Y/N.
      Creates the shared event or dismisses.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone

import functions_framework
from google.cloud import firestore

from ai_filter import evaluate_event
from calendar_service import create_notification_event, get_recent_events
from config import INITIAL_LOOKBACK_HOURS, USERS
from sms_service import (
    format_event_time,
    send_confirmation_sms,
    send_prompt_sms,
)

db = firestore.Client()


def _get_last_check_time(user_id: str) -> datetime:
    """Get the last time we checked this user's calendar."""
    doc = db.collection("app_state").document(f"last_check_{user_id}").get()
    if doc.exists:
        return doc.to_dict()["timestamp"]
    # First run: look back INITIAL_LOOKBACK_HOURS
    return datetime.now(timezone.utc) - timedelta(hours=INITIAL_LOOKBACK_HOURS)


def _set_last_check_time(user_id: str, timestamp: datetime) -> None:
    """Update the last check timestamp for a user."""
    db.collection("app_state").document(f"last_check_{user_id}").set(
        {"timestamp": timestamp}
    )


def _is_event_processed(event_id: str) -> bool:
    """Check if we've already processed this event."""
    doc = db.collection("processed_events").document(event_id).get()
    return doc.exists


def _mark_event_processed(event_id: str, user_id: str, action: str) -> None:
    """Mark an event as processed."""
    db.collection("processed_events").document(event_id).set({
        "user_id": user_id,
        "action": action,  # "prompted", "skipped_by_ai", "skipped_own_invite"
        "processed_at": datetime.now(timezone.utc),
    })


def _store_pending_prompt(
    prompt_id: str,
    user_id: str,
    event: dict,
    suggested_summary: str,
) -> None:
    """Store a pending SMS prompt in Firestore."""
    db.collection("pending_prompts").document(prompt_id).set({
        "user_id": user_id,
        "partner_id": USERS[user_id]["partner"],
        "event_id": event["id"],
        "event_summary": event["summary"],
        "event_start": event["start"],
        "event_end": event["end"],
        "event_all_day": event.get("all_day", False),
        "suggested_summary": suggested_summary,
        "partner_email": USERS[USERS[user_id]["partner"]]["email"],
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
    })


def _get_latest_pending_prompt(phone: str) -> dict | None:
    """Get the most recent pending prompt for a phone number.

    We match by phone number to figure out which user is replying.
    """
    # Find which user has this phone number
    user_id = None
    for uid, user in USERS.items():
        if user["phone"] == phone:
            user_id = uid
            break

    if user_id is None:
        return None

    # Get the most recent pending prompt for this user
    query = (
        db.collection("pending_prompts")
        .where("user_id", "==", user_id)
        .where("status", "==", "pending")
        .order_by("created_at", direction=firestore.Query.DESCENDING)
        .limit(1)
    )
    docs = list(query.stream())
    if not docs:
        return None

    data = docs[0].to_dict()
    data["doc_id"] = docs[0].id
    return data


@functions_framework.http
def check_new_events(request) -> tuple[str, int]:
    """Main check function — triggered hourly by Cloud Scheduler."""
    check_time = datetime.now(timezone.utc)
    results = {"users_checked": [], "events_found": 0, "prompts_sent": 0}

    for user_id, user_config in USERS.items():
        since = _get_last_check_time(user_id)
        partner_id = user_config["partner"]
        partner_email = USERS[partner_id]["email"]

        events = get_recent_events(user_id, since)
        results["users_checked"].append(user_id)
        results["events_found"] += len(events)

        for event in events:
            # Skip already-processed events
            if _is_event_processed(event["id"]):
                continue

            # Skip events that were created by the partner (these are
            # invites FROM the partner, which they already know about)
            if event.get("creator_email") == partner_email:
                _mark_event_processed(
                    event["id"], user_id, "skipped_own_invite"
                )
                continue

            # Run through AI filter
            ai_result = evaluate_event(event, user_id)

            if not ai_result["should_prompt"]:
                _mark_event_processed(
                    event["id"], user_id, f"skipped_by_ai: {ai_result['reason']}"
                )
                continue

            # Send SMS prompt
            event_time_str = format_event_time(
                event["start"], event.get("all_day", False)
            )

            prompt_id = str(uuid.uuid4())
            _store_pending_prompt(
                prompt_id, user_id, event, ai_result["suggested_summary"]
            )

            send_prompt_sms(
                to_phone=user_config["phone"],
                event_summary=event["summary"],
                event_time=event_time_str,
                partner_name=partner_id.capitalize(),
                suggested_summary=ai_result["suggested_summary"],
            )

            _mark_event_processed(event["id"], user_id, "prompted")
            results["prompts_sent"] += 1

        _set_last_check_time(user_id, check_time)

    return json.dumps(results), 200


@functions_framework.http
def handle_sms_reply(request) -> tuple[str, int]:
    """Handle incoming SMS replies from Twilio webhook.

    Twilio sends a POST with form data including:
        - From: the phone number that replied
        - Body: the reply text (Y/N)
    """
    from_phone = request.form.get("From", "")
    reply_body = request.form.get("Body", "").strip().upper()

    # Find the pending prompt for this phone number
    prompt = _get_latest_pending_prompt(from_phone)

    if prompt is None:
        # No pending prompt — could be a stale reply
        send_confirmation_sms(
            from_phone,
            "No pending event to respond to. You're all caught up!",
        )
        # Return TwiML empty response
        return '<Response></Response>', 200

    partner_name = prompt["partner_id"].capitalize()
    doc_ref = db.collection("pending_prompts").document(prompt["doc_id"])

    if reply_body in ("Y", "YES"):
        # Create the notification event
        create_notification_event(
            creator_user_id=prompt["user_id"],
            summary=prompt["suggested_summary"],
            start_time=prompt["event_start"],
            end_time=prompt["event_end"],
            invitee_email=prompt["partner_email"],
        )

        doc_ref.update({"status": "accepted"})

        send_confirmation_sms(
            from_phone,
            f"Done! Created \"{prompt['suggested_summary']}\" and "
            f"sent invite to {partner_name}.",
        )

    elif reply_body in ("N", "NO"):
        doc_ref.update({"status": "dismissed"})
        send_confirmation_sms(from_phone, "Got it, skipped.")

    else:
        send_confirmation_sms(
            from_phone,
            f"Reply Y to notify {partner_name} about "
            f"\"{prompt['event_summary']}\", or N to skip.",
        )

    # Return TwiML empty response
    return '<Response></Response>', 200
