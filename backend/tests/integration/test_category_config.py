import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def client():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_category_config_returns_correct_shape(client):
    resp = await client.get("/api/sessions/category-config")
    assert resp.status_code == 200
    data = resp.json()
    assert "overview_intro" in data
    assert len(data["overview_intro"]) > 0
    assert "categories" in data
    assert len(data["categories"]) == 8


async def test_category_config_strollers_is_ai(client):
    resp = await client.get("/api/sessions/category-config")
    data = resp.json()
    strollers = next(c for c in data["categories"] if c["id"] == "strollers")
    assert strollers["status"] == "ai"
    assert strollers["intro"] is not None


async def test_category_config_others_are_soon(client):
    resp = await client.get("/api/sessions/category-config")
    data = resp.json()
    for cat in data["categories"]:
        if cat["id"] != "strollers":
            assert cat["status"] == "soon"


async def test_category_config_no_session_required(client):
    # No cookie set — endpoint must still respond 200
    resp = await client.get("/api/sessions/category-config")
    assert resp.status_code == 200
