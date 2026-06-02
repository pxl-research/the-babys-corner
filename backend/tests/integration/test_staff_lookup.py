import pytest
import base64
import json
from datetime import datetime, timezone
from httpx import AsyncClient, ASGITransport


def basic_auth(username, password):
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


STAFF_CREDS = basic_auth("staff", "dev123")
WRONG_CREDS = basic_auth("staff", "wrongpass")


@pytest.fixture(autouse=True)
def set_staff_creds(monkeypatch):
    import app.config as cfg
    monkeypatch.setattr(cfg.settings, "staff_admin_username", "staff")
    monkeypatch.setattr(cfg.settings, "staff_admin_password", "dev123")


@pytest.fixture
async def client():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _create_and_handoff_session(client, source="home", profile_option=1):
    resp = await client.post(f"/api/sessions?source={source}")
    answers = [{"question_id": i + 1, "option_index": profile_option} for i in range(3)]
    await client.post("/api/sessions/current/quiz", json={"answers": answers, "optional_note": ""})
    await client.get("/api/sessions/current/recommendations?batch=1")
    await client.post("/api/sessions/current/handoff")
    session = await client.get("/api/sessions/current")
    return session.json()


async def test_staff_requires_basic_auth(client):
    resp = await client.get("/api/staff/sessions")
    assert resp.status_code == 401


async def test_staff_wrong_creds_rejected(client):
    resp = await client.get("/api/staff/sessions", headers=WRONG_CREDS)
    assert resp.status_code == 401


async def test_staff_recent_sessions_newest_first_limit_25(client):
    await _create_and_handoff_session(client)
    resp = await client.get("/api/staff/sessions", headers=STAFF_CREDS)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) <= 25


async def test_staff_code_search_returns_duplicate_matches(client):
    session_data = await _create_and_handoff_session(client)
    code = session_data["session_code"]
    resp = await client.get(f"/api/staff/sessions?code={code}", headers=STAFF_CREDS)
    assert resp.status_code == 200
    results = resp.json()
    assert any(s["session_code"] == code for s in results)


async def test_staff_filters_by_source(client):
    await _create_and_handoff_session(client, source="store")
    resp = await client.get("/api/staff/sessions?source=store", headers=STAFF_CREDS)
    assert resp.status_code == 200
    data = resp.json()
    assert all(s["source"] == "store" for s in data)


async def test_staff_home_email_failed_warning_only_for_home(client):
    from app.database import get_db
    session_data = await _create_and_handoff_session(client, source="home")
    code = session_data["session_code"]
    session_id = session_data["session_id"]

    db = await get_db()
    await db.execute("UPDATE sessions SET email_status='failed' WHERE session_id=?", (session_id,))
    await db.commit()

    resp = await client.get(f"/api/staff/sessions/{code}", headers=STAFF_CREDS)
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["email_failed_warning"] is True
