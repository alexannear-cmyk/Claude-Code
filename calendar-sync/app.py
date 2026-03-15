"""Calendar Sync — Main Flask app with background scheduler.

Run with: python app.py
"""

import json
import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, flash, redirect, render_template, request, url_for
from pywebpush import webpush, WebPushException

import database as db
from calendar_service import create_notification_event, get_recent_events
from config import (
    CHECK_INTERVAL_MINUTES,
    HOST,
    INITIAL_LOOKBACK_HOURS,
    PORT,
    SECRET_KEY,
    USERS,
    VAPID_CLAIM_EMAIL,
    VAPID_PRIVATE_KEY,
    VAPID_PUBLIC_KEY,
)
from event_filter import evaluate_event

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = SECRET_KEY


def check_new_events() -> dict:
    """Scan all users' calendars for new events and create prompts.

    This runs on a schedule (hourly by default).
    """
    check_time = datetime.now(timezone.utc)
    results = {"events_found": 0, "prompts_created": 0}

    for user_id, user_config in USERS.items():
        # Skip users without email configured
        if not user_config["email"]:
            continue

        partner_id = user_config["partner"]
        partner_email = USERS[partner_id]["email"]

        # Get last check time
        last_check_str = db.get_last_check_time(user_id)
        if last_check_str:
            since = datetime.fromisoformat(last_check_str)
        else:
            since = check_time - timedelta(hours=INITIAL_LOOKBACK_HOURS)

        try:
            events = get_recent_events(user_id, since)
        except ValueError as e:
            logger.warning("Skipping %s: %s", user_id, e)
            continue
        except Exception as e:
            logger.error("Error fetching events for %s: %s", user_id, e)
            continue

        results["events_found"] += len(events)

        for event in events:
            if db.is_event_processed(event["id"]):
                continue

            # Skip events created by the partner (they already know)
            if event.get("creator_email") == partner_email:
                db.mark_event_processed(event["id"], user_id, "skipped_partner_invite")
                continue

            # Run through filter
            filter_result = evaluate_event(event, user_id)

            if not filter_result["should_prompt"]:
                db.mark_event_processed(
                    event["id"], user_id, f"skipped: {filter_result['reason']}"
                )
                continue

            # Create a pending prompt
            db.store_pending_prompt(
                user_id=user_id,
                partner_id=partner_id,
                event_id=event["id"],
                event_summary=event["summary"],
                event_start=event["start"],
                event_end=event["end"],
                event_all_day=event.get("all_day", False),
                suggested_summary=filter_result["suggested_summary"],
                partner_email=partner_email,
            )
            db.mark_event_processed(event["id"], user_id, "prompted")
            results["prompts_created"] += 1

            logger.info(
                "New prompt: %s -> notify %s about '%s'",
                user_id, partner_id, event["summary"],
            )

        db.set_last_check_time(user_id, check_time.isoformat())

    logger.info(
        "Check complete: %d events found, %d prompts created",
        results["events_found"], results["prompts_created"],
    )

    if results["prompts_created"] > 0:
        send_push_notifications(
            title="Calendar Sync",
            body=f"{results['prompts_created']} new event(s) to review",
        )

    return results


def send_push_notifications(title: str, body: str) -> None:
    """Send a push notification to all stored subscriptions."""
    if not VAPID_PRIVATE_KEY:
        logger.warning("VAPID_PRIVATE_KEY not set, skipping push notifications")
        return

    payload = json.dumps({"title": title, "body": body})
    for sub_json in db.get_all_push_subscriptions():
        try:
            webpush(
                subscription_info=json.loads(sub_json),
                data=payload,
                vapid_private_key=VAPID_PRIVATE_KEY,
                vapid_claims={"sub": VAPID_CLAIM_EMAIL},
            )
        except WebPushException as e:
            if e.response and e.response.status_code in (404, 410):
                endpoint = json.loads(sub_json)["endpoint"]
                db.delete_push_subscription(endpoint)
                logger.info("Removed stale push subscription: %s", endpoint[:60])
            else:
                logger.error("Push failed: %s", e)


@app.route("/service-worker.js")
def service_worker():
    """Serve service worker from root scope."""
    return app.send_static_file("service-worker.js"), 200, {
        "Content-Type": "application/javascript",
        "Service-Worker-Allowed": "/",
    }


@app.route("/")
def dashboard():
    """Main dashboard showing pending prompts and recent history."""
    pending = db.get_pending_prompts()
    history = db.get_recent_history(limit=20)

    last_check = db.get_last_check_time("alex") or db.get_last_check_time("sara")

    return render_template(
        "dashboard.html",
        pending=pending,
        history=history,
        last_check=last_check,
    )


@app.route("/respond/<int:prompt_id>", methods=["POST"])
def respond(prompt_id: int):
    """Handle accept/dismiss actions from the dashboard."""
    action = request.form.get("action")
    prompt = db.get_prompt_by_id(prompt_id)

    if not prompt:
        flash("Prompt not found.", "error")
        return redirect(url_for("dashboard"))

    if prompt["status"] != "pending":
        flash("This prompt has already been handled.", "error")
        return redirect(url_for("dashboard"))

    if action == "accept":
        try:
            create_notification_event(
                creator_user_id=prompt["user_id"],
                summary=prompt["suggested_summary"],
                start_time=prompt["event_start"],
                end_time=prompt["event_end"],
                invitee_email=prompt["partner_email"],
            )
            db.update_prompt_status(prompt_id, "accepted")
            flash(
                f"Created \"{prompt['suggested_summary']}\" and "
                f"sent invite to {prompt['partner_id'].capitalize()}!",
                "success",
            )
        except Exception as e:
            logger.error("Failed to create event: %s", e)
            flash(f"Error creating event: {e}", "error")

    elif action == "dismiss":
        db.update_prompt_status(prompt_id, "dismissed")
        flash("Skipped.", "success")

    return redirect(url_for("dashboard"))


@app.route("/push/vapid-public-key")
def vapid_public_key():
    """Serve the VAPID public key for push subscription."""
    return VAPID_PUBLIC_KEY


@app.route("/push/subscribe", methods=["POST"])
def push_subscribe():
    """Store a push subscription from the browser."""
    subscription = request.get_json()
    if not subscription or "endpoint" not in subscription:
        return "Invalid subscription", 400
    db.save_push_subscription(json.dumps(subscription))
    return "OK", 201


@app.route("/check", methods=["POST"])
def manual_check():
    """Manually trigger a calendar check."""
    results = check_new_events()
    flash(
        f"Check complete: {results['events_found']} events found, "
        f"{results['prompts_created']} new prompts.",
        "success",
    )
    return redirect(url_for("dashboard"))


def main():
    # Initialize database
    db.init_db()

    # Set up background scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        check_new_events,
        "interval",
        minutes=CHECK_INTERVAL_MINUTES,
        id="calendar_check",
        next_run_time=None,  # Don't run immediately on startup
    )
    scheduler.start()
    logger.info(
        "Scheduler started — checking every %d minutes", CHECK_INTERVAL_MINUTES
    )

    # Run Flask
    try:
        app.run(host=HOST, port=PORT, debug=False)
    finally:
        scheduler.shutdown()


if __name__ == "__main__":
    main()
