"""Rule-based event filtering — no API cost.

Determines whether a calendar event is worth prompting the user
to share with their partner.
"""

import re

from config import USERS

# Keywords that suggest the event should be shared
SHARE_KEYWORDS = [
    # Social
    "dinner", "lunch", "brunch", "breakfast", "drinks", "happy hour",
    "party", "hangout", "hang out", "get together", "get-together",
    "gathering", "meetup", "meet up", "meet-up",
    # Activities
    "movie", "concert", "show", "game", "match", "festival", "event",
    "hike", "hiking", "camping", "trip", "travel", "flight", "hotel",
    "vacation", "road trip",
    # Appointments
    "doctor", "dentist", "vet", "veterinarian", "appointment", "checkup",
    "check-up", "physical", "therapy", "therapist", "counseling",
    "optometrist", "dermatologist",
    # Errands / commitments
    "pickup", "pick up", "pick-up", "drop off", "drop-off", "dropoff",
    "haircut", "salon", "barber",
    # Kids / family
    "school", "recital", "practice", "game day", "conference",
    "parent-teacher", "playdate", "play date",
    # Location indicators
    "at ", "going to", "heading to",
]

# Keywords that suggest the event should be skipped
SKIP_KEYWORDS = [
    # Work
    "standup", "stand-up", "stand up", "sync", "1:1", "one on one",
    "sprint", "retro", "retrospective", "planning", "scrum",
    "all-hands", "all hands", "team meeting", "staff meeting",
    "interview", "onboarding",
    # Focus / personal workflow
    "focus", "deep work", "block", "hold", "busy", "do not disturb",
    "dnd", "heads down",
    # Recurring personal
    "gym", "workout", "exercise", "run", "yoga", "meditation",
    "journal", "morning routine",
    # Calendar noise
    "reminder", "todo", "to-do", "to do", "task",
    "birthday", "holiday", "anniversary",  # Usually on shared calendars
    "ooo", "out of office", "pto", "time off",
]

# Calendar names that are typically work-related
WORK_CALENDAR_KEYWORDS = [
    "work", "office", "job", "meetings",
]


def evaluate_event(event: dict, creator_user_id: str) -> dict:
    """Evaluate whether a calendar event should be shared with the partner.

    Uses keyword-based rules instead of an API call — completely free.

    Args:
        event: Event dict with keys: summary, calendar_name, start, end,
               description, location, all_day
        creator_user_id: The user who created the event (e.g., "alex")

    Returns:
        dict with keys:
            - should_prompt (bool)
            - reason (str)
            - suggested_summary (str)
    """
    creator_name = creator_user_id.capitalize()
    summary = event.get("summary", "").lower()
    description = event.get("description", "").lower()
    calendar_name = event.get("calendar_name", "").lower()
    location = event.get("location", "")
    combined_text = f"{summary} {description}"

    # Check if it's from a work calendar — skip by default
    for keyword in WORK_CALENDAR_KEYWORDS:
        if keyword in calendar_name:
            # Even work calendars might have share-worthy events
            # (e.g., "work trip to Austin"), so check share keywords first
            has_share_keyword = any(kw in combined_text for kw in SHARE_KEYWORDS)
            if not has_share_keyword:
                return {
                    "should_prompt": False,
                    "reason": f"Work calendar event: {event.get('summary', '')}",
                    "suggested_summary": "",
                }

    # Check skip keywords first
    for keyword in SKIP_KEYWORDS:
        if keyword in combined_text:
            # But override if there's also a strong share signal
            has_share_keyword = any(kw in combined_text for kw in SHARE_KEYWORDS)
            if not has_share_keyword:
                return {
                    "should_prompt": False,
                    "reason": f"Matches skip keyword: {keyword}",
                    "suggested_summary": "",
                }

    # Check share keywords
    for keyword in SHARE_KEYWORDS:
        if keyword in combined_text:
            suggested = _build_summary(creator_name, event)
            return {
                "should_prompt": True,
                "reason": f"Matches share keyword: {keyword}",
                "suggested_summary": suggested,
            }

    # If there's a location, it's probably worth sharing
    if location:
        suggested = _build_summary(creator_name, event)
        return {
            "should_prompt": True,
            "reason": "Event has a location set",
            "suggested_summary": suggested,
        }

    # Default: skip (avoids over-notifying)
    return {
        "should_prompt": False,
        "reason": "No share signals detected",
        "suggested_summary": "",
    }


def _build_summary(creator_name: str, event: dict) -> str:
    """Build a concise notification summary from the event."""
    summary = event.get("summary", "(no title)")
    location = event.get("location", "")

    # Try to extract a short activity description
    activity = summary

    # Remove common prefixes people use
    for prefix in ["Going to ", "going to ", "Heading to ", "heading to "]:
        if activity.startswith(prefix):
            activity = activity[len(prefix):]
            break

    if location:
        # Shorten location to just the venue name if possible
        short_location = location.split(",")[0].strip()
        return f"{creator_name} at {activity} ({short_location})"

    return f"{creator_name} — {activity}"
