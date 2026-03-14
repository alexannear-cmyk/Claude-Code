"""AI-powered event filtering using Claude API."""

import json

import anthropic

from config import ANTHROPIC_API_KEY, USERS

_client = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


def evaluate_event(event: dict, creator_user_id: str) -> dict:
    """Evaluate whether a calendar event should be shared with the partner.

    Args:
        event: Event dict from calendar_service.get_recent_events()
        creator_user_id: The user who created the event (e.g., "alex")

    Returns:
        dict with keys:
            - should_prompt (bool): Whether to ask the user about sharing
            - reason (str): Brief explanation
            - suggested_summary (str): Suggested title for the notification event
    """
    creator = USERS[creator_user_id]
    partner_id = creator["partner"]
    partner = USERS[partner_id]

    creator_name = creator_user_id.capitalize()
    partner_name = partner_id.capitalize()

    prompt = f"""You are helping a couple ({creator_name} and {partner_name}) stay informed about each other's schedules. Given this calendar event created by {creator_name}, determine if {partner_name} likely needs to know about it.

Event: {event['summary']}
Calendar: {event['calendar_name']}
Time: {event['start']} - {event['end']}
Location: {event.get('location', 'N/A')}
Description: {event.get('description', 'N/A')}
All-day event: {event.get('all_day', False)}

SHARE if the event involves: social plans, appointments (doctor, dentist, etc.), travel, commitments that affect availability at home, activities outside the home, events involving other people, dinners/outings, picking up kids, etc.

SKIP if the event is: a work meeting, focus/deep work block, personal reminder or to-do, recurring daily habit (gym routine, etc.), trivial calendar hold, birthday/holiday that's already on shared calendars, lunch break, or something clearly internal to one person's workflow.

Respond with ONLY valid JSON (no markdown, no code fences):
{{"should_prompt": true/false, "reason": "brief explanation", "suggested_summary": "{creator_name} at [activity] ([location if relevant])"}}

The suggested_summary should be concise and informative from {partner_name}'s perspective. Examples:
- "Alex at doctor appointment"
- "Sara at dinner with friends (downtown)"
- "Alex traveling to Austin"
- "Sara at parent-teacher conference"
"""

    client = _get_client()
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        # If parsing fails, default to prompting (safer to over-ask than miss)
        return {
            "should_prompt": True,
            "reason": "Could not parse AI response; prompting as a precaution.",
            "suggested_summary": f"{creator_name} — {event['summary']}",
        }

    return {
        "should_prompt": bool(result.get("should_prompt", True)),
        "reason": result.get("reason", ""),
        "suggested_summary": result.get(
            "suggested_summary",
            f"{creator_name} — {event['summary']}",
        ),
    }
