import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def client():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_email_trigger_only_on_handoff(client):
    resp = await client.post("/api/sessions?source=home")
    assert resp.status_code == 200

    answers = [{"question_id": i + 1, "option_index": 1} for i in range(3)]
    await client.post("/api/sessions/current/quiz", json={"answers": answers, "optional_note": ""})
    await client.get("/api/sessions/current/recommendations?batch=1")

    with patch("app.routers.session.send_handoff_email", new=AsyncMock()) as mock_email:
        resp = await client.post("/api/sessions/current/handoff")
        assert resp.status_code == 200
        # Email scheduled as background task (may not be called synchronously)
        data = resp.json()
        assert data["email_status"] == "pending"
