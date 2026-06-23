import pytest
import base64
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
    await client.post(f"/api/sessions?source={source}")
    answers = [{"question_id": i + 1, "option_index": profile_option} for i in range(2)]
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


async def test_staff_detail_resolves_product_names(client):
    session_data = await _create_and_handoff_session(client, source="store")
    code = session_data["session_code"]

    resp = await client.get(f"/api/staff/sessions/{code}", headers=STAFF_CREDS)
    assert resp.status_code == 200
    detail = resp.json()
    # Shown products are resolved to named objects (with thumbnail), not bare IDs.
    assert detail["shown_products_named"]
    first = detail["shown_products_named"][0][0]
    assert set(first.keys()) == {"id", "name", "brand", "image_url", "price"}
    assert first["name"]


async def test_staff_detail_includes_tag_answers(client):
    await client.post("/api/sessions?source=store")
    answers = [{"question_id": i + 1, "option_index": 1} for i in range(2)]
    await client.post("/api/sessions/current/quiz", json={"answers": answers, "optional_note": ""})
    tag_answers = [
        {"question_id": "usage", "option_indices": [1]},
        {"question_id": "start_age", "option_indices": [0]},
        {"question_id": "fold", "option_indices": []},          # skipped
        {"question_id": "comfort", "option_indices": [0, 2]},   # multi-select
    ]
    await client.post("/api/sessions/current/tag-quiz", json={"answers": tag_answers})
    await client.get("/api/sessions/current/recommendations?batch=1")
    code = (await client.get("/api/sessions/current")).json()["session_code"]
    await client.post("/api/sessions/current/handoff")

    detail = (await client.get(f"/api/staff/sessions/{code}", headers=STAFF_CREDS)).json()
    ta = detail["tag_answers"]
    assert len(ta) == 4
    assert all(a["question_text"] for a in ta)
    assert any(a["option_text"] == "Overgeslagen" for a in ta)   # skipped question recorded
    assert any(", " in a["option_text"] for a in ta)             # multi-select joined


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
