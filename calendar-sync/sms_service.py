"""SMS notification system using Twilio."""

from twilio.rest import Client

from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER

_client = None


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    return _client


def send_prompt_sms(
    to_phone: str,
    event_summary: str,
    event_time: str,
    partner_name: str,
    suggested_summary: str,
) -> str:
    """Send an SMS prompting the user to share an event with their partner.

    Args:
        to_phone: Phone number to send to (E.164 format, e.g., "+15551234567")
        event_summary: Original event title
        event_time: Human-readable event time string
        partner_name: Name of the partner (e.g., "Sara")
        suggested_summary: AI-suggested notification title

    Returns:
        Twilio message SID
    """
    body = (
        f'New event: "{event_summary}"\n'
        f"{event_time}\n"
        f"\n"
        f'Notify {partner_name}? (as "{suggested_summary}")\n'
        f"Reply Y or N"
    )

    client = _get_client()
    message = client.messages.create(
        body=body,
        from_=TWILIO_PHONE_NUMBER,
        to=to_phone,
    )

    return message.sid


def send_confirmation_sms(to_phone: str, message: str) -> str:
    """Send a confirmation SMS after the user replies.

    Args:
        to_phone: Phone number to send to
        message: Confirmation message text

    Returns:
        Twilio message SID
    """
    client = _get_client()
    msg = client.messages.create(
        body=message,
        from_=TWILIO_PHONE_NUMBER,
        to=to_phone,
    )
    return msg.sid


def format_event_time(start: str, all_day: bool) -> str:
    """Format an event's start time for display in SMS.

    Args:
        start: ISO 8601 datetime or date string
        all_day: Whether this is an all-day event

    Returns:
        Human-readable time string
    """
    from datetime import datetime

    if all_day:
        dt = datetime.strptime(start[:10], "%Y-%m-%d")
        return dt.strftime("%A, %B %-d (all day)")

    try:
        # Handle datetime with timezone offset
        dt = datetime.fromisoformat(start)
        return dt.strftime("%A, %B %-d at %-I:%M %p")
    except ValueError:
        return start
