"""Tests for the Flask web dashboard."""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import database as db


@pytest.fixture
def client():
    """Create a test Flask client with a temporary database."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    test_db = tmp.name

    # Patch DATABASE_PATH before importing app
    import config
    original_db_path = config.DATABASE_PATH
    config.DATABASE_PATH = test_db

    # Also patch the database module's default
    import database
    db.init_db(test_db)

    from app import app
    app.config["TESTING"] = True

    with app.test_client() as client:
        yield client, test_db

    # Cleanup
    config.DATABASE_PATH = original_db_path
    if os.path.exists(test_db):
        os.unlink(test_db)


def test_dashboard_loads(client):
    client, test_db = client
    response = client.get("/")
    assert response.status_code == 200
    assert b"Calendar Sync" in response.data
    assert b"all caught up" in response.data


def test_dashboard_shows_pending_prompts(client):
    client, test_db = client
    db.store_pending_prompt(
        user_id="alex",
        partner_id="sara",
        event_id="evt1",
        event_summary="Movie at Alamo",
        event_start="2026-03-18T18:00:00-05:00",
        event_end="2026-03-18T20:00:00-05:00",
        event_all_day=False,
        suggested_summary="Alex at movie (Alamo Drafthouse)",
        partner_email="annear.sara@gmail.com",
        db_path=test_db,
    )
    response = client.get("/")
    assert response.status_code == 200
    assert b"Movie at Alamo" in response.data
    assert b"Alex at movie" in response.data


def test_dismiss_prompt(client):
    client, test_db = client
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
        db_path=test_db,
    )
    response = client.post(
        f"/respond/{prompt_id}",
        data={"action": "dismiss"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Skipped" in response.data

    # Verify it's no longer pending
    pending = db.get_pending_prompts(db_path=test_db)
    assert len(pending) == 0


def test_respond_nonexistent_prompt(client):
    client, test_db = client
    response = client.post(
        "/respond/9999",
        data={"action": "accept"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"not found" in response.data


def test_respond_already_handled(client):
    client, test_db = client
    prompt_id = db.store_pending_prompt(
        user_id="alex",
        partner_id="sara",
        event_id="evt1",
        event_summary="Test event",
        event_start="2026-03-18T18:00:00-05:00",
        event_end="2026-03-18T19:00:00-05:00",
        event_all_day=False,
        suggested_summary="Alex — Test event",
        partner_email="annear.sara@gmail.com",
        db_path=test_db,
    )
    db.update_prompt_status(prompt_id, "dismissed", test_db)

    response = client.post(
        f"/respond/{prompt_id}",
        data={"action": "accept"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"already been handled" in response.data
