import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def client():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_instore_handoff_returns_staff_context(client):
    resp = await client.post("/api/sessions?source=store")
    assert resp.status_code == 200

    answers = [{"question_id": i + 1, "option_index": 2} for i in range(3)]
    await client.post("/api/sessions/current/quiz", json={"answers": answers, "optional_note": ""})
    await client.get("/api/sessions/current/recommendations?batch=1")

    resp = await client.post("/api/sessions/current/handoff")
    assert resp.status_code == 200
    data = resp.json()
    assert "session_code" in data
    assert "handoff_at" in data


async def test_instore_inactivity_abandon_marks_abandoned_without_email(client):
    resp = await client.post("/api/sessions?source=store")
    assert resp.status_code == 200

    answers = [{"question_id": i + 1, "option_index": 0} for i in range(3)]
    await client.post("/api/sessions/current/quiz", json={"answers": answers, "optional_note": ""})

    resp = await client.post("/api/sessions/current/abandon")
    assert resp.status_code == 200

    current = await client.get("/api/sessions/current")
    assert current.json()["status"] == "abandoned"
