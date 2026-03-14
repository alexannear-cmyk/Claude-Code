"""Tests for database operations."""

import os
import tempfile

import pytest

# Set DATABASE_PATH before importing database module
_tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp.close()
TEST_DB = _tmp.name

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import database as db


@pytest.fixture(autouse=True)
def fresh_db():
    """Initialize a fresh database for each test."""
    # Remove and recreate
    if os.path.exists(TEST_DB):
        os.unlink(TEST_DB)
    db.init_db(TEST_DB)
    yield
    if os.path.exists(TEST_DB):
        os.unlink(TEST_DB)


def test_init_db_creates_tables():
    conn = db.get_connection(TEST_DB)
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    conn.close()
    table_names = {row["name"] for row in tables}
    assert "processed_events" in table_names
    assert "pending_prompts" in table_names
    assert "app_state" in table_names


def test_event_processed_lifecycle():
    assert db.is_event_processed("evt1", TEST_DB) is False
    db.mark_event_processed("evt1", "alex", "prompted", TEST_DB)
    assert db.is_event_processed("evt1", TEST_DB) is True


def test_mark_event_processed_is_idempotent():
    db.mark_event_processed("evt1", "alex", "prompted", TEST_DB)
    db.mark_event_processed("evt1", "alex", "skipped", TEST_DB)
    assert db.is_event_processed("evt1", TEST_DB) is True


def test_pending_prompt_lifecycle():
    # Store a prompt
    prompt_id = db.store_pending_prompt(
        user_id="alex",
        partner_id="sara",
        event_id="evt1",
        event_summary="Movie at Alamo",
        event_start="2026-03-18T18:00:00-05:00",
        event_end="2026-03-18T20:00:00-05:00",
        event_all_day=False,
        suggested_summary="Alex at movie (Alamo Drafthouse)",
        partner_email="annear.sara@gmail.com",
        db_path=TEST_DB,
    )
    assert prompt_id is not None

    # Fetch pending
    pending = db.get_pending_prompts(db_path=TEST_DB)
    assert len(pending) == 1
    assert pending[0]["event_summary"] == "Movie at Alamo"
    assert pending[0]["status"] == "pending"

    # Filter by user
    alex_pending = db.get_pending_prompts("alex", TEST_DB)
    assert len(alex_pending) == 1
    sara_pending = db.get_pending_prompts("sara", TEST_DB)
    assert len(sara_pending) == 0

    # Accept
    db.update_prompt_status(prompt_id, "accepted", TEST_DB)
    pending = db.get_pending_prompts(db_path=TEST_DB)
    assert len(pending) == 0

    # Verify in history
    history = db.get_recent_history(limit=10, db_path=TEST_DB)
    assert len(history) == 1
    assert history[0]["status"] == "accepted"


def test_get_prompt_by_id():
    prompt_id = db.store_pending_prompt(
        user_id="sara",
        partner_id="alex",
        event_id="evt2",
        event_summary="Dinner with friends",
        event_start="2026-03-20T19:00:00-05:00",
        event_end="2026-03-20T21:00:00-05:00",
        event_all_day=False,
        suggested_summary="Sara at dinner with friends",
        partner_email="alex@gmail.com",
        db_path=TEST_DB,
    )
    prompt = db.get_prompt_by_id(prompt_id, TEST_DB)
    assert prompt is not None
    assert prompt["event_summary"] == "Dinner with friends"

    # Non-existent ID
    assert db.get_prompt_by_id(9999, TEST_DB) is None


def test_app_state_last_check():
    assert db.get_last_check_time("alex", TEST_DB) is None
    db.set_last_check_time("alex", "2026-03-14T12:00:00+00:00", TEST_DB)
    assert db.get_last_check_time("alex", TEST_DB) == "2026-03-14T12:00:00+00:00"

    # Update
    db.set_last_check_time("alex", "2026-03-14T13:00:00+00:00", TEST_DB)
    assert db.get_last_check_time("alex", TEST_DB) == "2026-03-14T13:00:00+00:00"


def test_recent_history_limit():
    for i in range(25):
        db.store_pending_prompt(
            user_id="alex",
            partner_id="sara",
            event_id=f"evt_{i}",
            event_summary=f"Event {i}",
            event_start="2026-03-18T18:00:00",
            event_end="2026-03-18T19:00:00",
            event_all_day=False,
            suggested_summary=f"Alex — Event {i}",
            partner_email="sara@gmail.com",
            db_path=TEST_DB,
        )
    history = db.get_recent_history(limit=10, db_path=TEST_DB)
    assert len(history) == 10
