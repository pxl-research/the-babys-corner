import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def client():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _start_session(client):
    await client.post("/api/sessions?source=home")
    answers = [{"question_id": i + 1, "option_index": 0} for i in range(2)]
    await client.post("/api/sessions/current/quiz", json={"answers": answers, "optional_note": ""})


async def _set_status(reset_db, status):
    await reset_db.execute("UPDATE sessions SET status=?", (status,))
    await reset_db.commit()


async def test_schema_creates_sessions_table_with_required_columns(reset_db):
    async with reset_db.execute("PRAGMA table_info(sessions)") as cursor:
        cols = {row["name"] async for row in cursor}
    required = {
        "session_id", "session_code", "source", "status", "started_at",
        "quiz_submitted_at", "first_reco_at", "handoff_at", "quiz_answers",
        "optional_note", "derived_profile", "shown_products",
        "stroller_favorites", "accessory_favorites", "reco_order",
        "extra_reco_order", "favorites_adaptation_active", "email_status",
        "email_retry_count", "email_last_attempt", "llm_key_features",
        "llm_talking_points", "llm_ranking_output", "llm_similarity_output",
    }
    assert required.issubset(cols)


async def test_handed_off_session_rejects_quiz_submit(client, reset_db):
    await client.post("/api/sessions?source=home")
    await _set_status(reset_db, "handed_off")
    answers = [{"question_id": i + 1, "option_index": 0} for i in range(2)]
    resp = await client.post("/api/sessions/current/quiz", json={"answers": answers, "optional_note": ""})
    assert resp.status_code == 409


async def test_handed_off_session_rejects_favorite_toggle(client, reset_db):
    await _start_session(client)
    await _set_status(reset_db, "handed_off")
    resp = await client.post(
        "/api/sessions/current/favorites", json={"item_id": "x", "item_type": "stroller"}
    )
    assert resp.status_code == 409


async def test_abandoned_session_rejects_favorite_toggle(client, reset_db):
    await _start_session(client)
    await _set_status(reset_db, "abandoned")
    resp = await client.post(
        "/api/sessions/current/favorites", json={"item_id": "x", "item_type": "stroller"}
    )
    assert resp.status_code == 409


async def test_handed_off_session_rejects_tag_quiz(client, reset_db):
    await _start_session(client)
    await _set_status(reset_db, "handed_off")
    resp = await client.post("/api/sessions/current/tag-quiz", json={"answers": []})
    assert resp.status_code == 409


async def test_locked_session_still_allows_current_read(client, reset_db):
    await _start_session(client)
    await _set_status(reset_db, "handed_off")
    resp = await client.get("/api/sessions/current")
    assert resp.status_code == 200
    assert resp.json()["status"] == "handed_off"


async def test_handoff_rejects_abandoned_session(client, reset_db):
    await _start_session(client)
    await _set_status(reset_db, "abandoned")
    resp = await client.post("/api/sessions/current/handoff")
    assert resp.status_code == 409


async def test_abandon_rejects_handed_off_session(client, reset_db):
    await _start_session(client)
    await _set_status(reset_db, "handed_off")
    resp = await client.post("/api/sessions/current/abandon")
    assert resp.status_code == 409
