"""Tests for rule-based event filtering."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from event_filter import evaluate_event


def _make_event(summary, calendar_name="General", location="", description=""):
    return {
        "summary": summary,
        "calendar_name": calendar_name,
        "start": "2026-03-18T18:00:00-05:00",
        "end": "2026-03-18T19:00:00-05:00",
        "location": location,
        "description": description,
        "all_day": False,
    }


# --- Events that SHOULD be shared ---

def test_dinner_is_shared():
    result = evaluate_event(_make_event("Dinner with friends"), "alex")
    assert result["should_prompt"] is True
    assert "Alex" in result["suggested_summary"]


def test_doctor_appointment_is_shared():
    result = evaluate_event(_make_event("Doctor appointment"), "alex")
    assert result["should_prompt"] is True


def test_movie_is_shared():
    result = evaluate_event(_make_event("Movie night"), "sara")
    assert result["should_prompt"] is True
    assert "Sara" in result["suggested_summary"]


def test_trip_is_shared():
    result = evaluate_event(_make_event("Trip to Austin"), "alex")
    assert result["should_prompt"] is True


def test_event_with_location_is_shared():
    result = evaluate_event(
        _make_event("Something", location="123 Main St"), "alex"
    )
    assert result["should_prompt"] is True


def test_concert_is_shared():
    result = evaluate_event(_make_event("Concert at Moody Center"), "sara")
    assert result["should_prompt"] is True


def test_haircut_is_shared():
    result = evaluate_event(_make_event("Haircut"), "alex")
    assert result["should_prompt"] is True


def test_drinks_is_shared():
    result = evaluate_event(_make_event("Drinks with coworkers"), "alex")
    assert result["should_prompt"] is True


def test_pick_up_kids_is_shared():
    result = evaluate_event(_make_event("Pick up kids from school"), "sara")
    assert result["should_prompt"] is True


# --- Events that should be SKIPPED ---

def test_standup_is_skipped():
    result = evaluate_event(_make_event("Daily standup"), "alex")
    assert result["should_prompt"] is False


def test_focus_time_is_skipped():
    result = evaluate_event(_make_event("Focus time"), "alex")
    assert result["should_prompt"] is False


def test_work_meeting_on_work_calendar_is_skipped():
    result = evaluate_event(
        _make_event("Q4 Planning", calendar_name="Work"), "alex"
    )
    assert result["should_prompt"] is False


def test_gym_is_skipped():
    result = evaluate_event(_make_event("Gym"), "alex")
    assert result["should_prompt"] is False


def test_reminder_is_skipped():
    result = evaluate_event(_make_event("Reminder: pay bills"), "alex")
    assert result["should_prompt"] is False


def test_one_on_one_is_skipped():
    result = evaluate_event(_make_event("1:1 with manager"), "alex")
    assert result["should_prompt"] is False


def test_generic_event_without_keywords_is_skipped():
    result = evaluate_event(_make_event("Something"), "alex")
    assert result["should_prompt"] is False


# --- Summary formatting ---

def test_summary_includes_location():
    result = evaluate_event(
        _make_event("Movie", location="Alamo Drafthouse, Austin TX"),
        "alex",
    )
    assert result["should_prompt"] is True
    assert "Alamo Drafthouse" in result["suggested_summary"]
    assert "Alex" in result["suggested_summary"]


def test_summary_strips_going_to_prefix():
    result = evaluate_event(
        _make_event("Going to dinner", location="Uchi"),
        "sara",
    )
    assert result["should_prompt"] is True
    # Should not start with "Sara at Going to..."
    assert "Going to" not in result["suggested_summary"]


# --- Edge cases ---

def test_work_calendar_with_share_keyword_is_shared():
    """Work trip on a work calendar should still be shared."""
    result = evaluate_event(
        _make_event("Work trip to NYC", calendar_name="Work"), "alex"
    )
    assert result["should_prompt"] is True


def test_description_keywords_are_checked():
    result = evaluate_event(
        _make_event("Plans", description="dinner with the group"), "alex"
    )
    assert result["should_prompt"] is True
