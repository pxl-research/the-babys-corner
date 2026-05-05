import pytest
import json
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def client():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_quiz_config_returns_config_driven_copy(client):
    resp = await client.get("/api/sessions/quiz-config")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["questions"]) == 5
    assert data["optional_note"]["skip_label"] == "Niet nodig"


async def test_full_flow_submits_optional_note_on_step_six_then_stable_recommendations(client):
    # Create session
    resp = await client.post("/api/sessions?source=home")
    assert resp.status_code == 200
    # Check cookie set
    assert "session_id" in resp.cookies

    # Submit quiz with optional note
    answers = [{"question_id": i + 1, "option_index": 1} for i in range(5)]
    resp = await client.post(
        "/api/sessions/current/quiz",
        json={"answers": answers, "optional_note": "We houden van stijl"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "profile" in data
    assert "transition_phrase" in data

    # Fetch batch 1
    resp1 = await client.get("/api/sessions/current/recommendations?batch=1")
    assert resp1.status_code == 200
    batch1 = resp1.json()
    assert batch1["batch"] == 1
    ids1 = [p["id"] for p in batch1["products"]]

    # Fetch batch 1 again — must be stable
    resp1b = await client.get("/api/sessions/current/recommendations?batch=1")
    ids1b = [p["id"] for p in resp1b.json()["products"]]
    assert ids1 == ids1b


async def test_no_optional_note_skips_llm_ranking(client):
    resp = await client.post("/api/sessions?source=home")
    assert resp.status_code == 200

    answers = [{"question_id": i + 1, "option_index": 0} for i in range(5)]
    resp = await client.post(
        "/api/sessions/current/quiz",
        json={"answers": answers, "optional_note": ""},
    )
    assert resp.status_code == 200


async def test_handoff_sets_pending_email_and_locks_session(client):
    resp = await client.post("/api/sessions?source=home")
    assert resp.status_code == 200

    answers = [{"question_id": i + 1, "option_index": 1} for i in range(5)]
    await client.post("/api/sessions/current/quiz", json={"answers": answers, "optional_note": ""})
    await client.get("/api/sessions/current/recommendations?batch=1")

    resp = await client.post("/api/sessions/current/handoff")
    assert resp.status_code == 200
    data = resp.json()
    assert data["email_status"] == "pending"
    assert "session_code" in data

    # Session is now locked
    current = await client.get("/api/sessions/current")
    assert current.json()["status"] == "handed_off"


async def test_after_handoff_favorite_toggle_returns_409(client):
    resp = await client.post("/api/sessions?source=home")
    assert resp.status_code == 200

    answers = [{"question_id": i + 1, "option_index": 1} for i in range(5)]
    await client.post("/api/sessions/current/quiz", json={"answers": answers, "optional_note": ""})
    await client.get("/api/sessions/current/recommendations?batch=1")
    await client.post("/api/sessions/current/handoff")

    resp = await client.post(
        "/api/sessions/current/favorites",
        json={"item_id": "ST001", "item_type": "stroller"},
    )
    assert resp.status_code == 409


async def test_after_handoff_new_batch_returns_409(client):
    resp = await client.post("/api/sessions?source=home")
    assert resp.status_code == 200

    answers = [{"question_id": i + 1, "option_index": 1} for i in range(5)]
    await client.post("/api/sessions/current/quiz", json={"answers": answers, "optional_note": ""})
    await client.get("/api/sessions/current/recommendations?batch=1")
    await client.post("/api/sessions/current/handoff")

    resp = await client.get("/api/sessions/current/recommendations?batch=2")
    assert resp.status_code == 409


async def test_abandon_after_handoff_returns_409(client):
    resp = await client.post("/api/sessions?source=home")
    assert resp.status_code == 200

    answers = [{"question_id": i + 1, "option_index": 1} for i in range(5)]
    await client.post("/api/sessions/current/quiz", json={"answers": answers, "optional_note": ""})
    await client.get("/api/sessions/current/recommendations?batch=1")
    await client.post("/api/sessions/current/handoff")

    resp = await client.post("/api/sessions/current/abandon")
    assert resp.status_code == 409


async def test_recommendations_generate_and_cache_llm_key_features(client, reset_db):
    resp = await client.post("/api/sessions?source=home")
    assert resp.status_code == 200

    answers = [{"question_id": i + 1, "option_index": 1} for i in range(5)]
    await client.post("/api/sessions/current/quiz", json={"answers": answers, "optional_note": ""})

    with patch("app.routers.session.generate_key_features", new=AsyncMock(return_value="Compact en wendbaar.")):
        resp = await client.get("/api/sessions/current/recommendations?batch=1")

    assert resp.status_code == 200
    product_ids = [p["id"] for p in resp.json()["products"]]

    async with reset_db.execute("SELECT llm_key_features FROM sessions") as cur:
        row = await cur.fetchone()

    cached = json.loads(row["llm_key_features"])
    assert set(product_ids).issubset(cached.keys())
    assert all(cached[id_] == "Compact en wendbaar." for id_ in product_ids)


async def test_handoff_generates_talking_points_in_background(client, reset_db):
    resp = await client.post("/api/sessions?source=home")
    assert resp.status_code == 200

    answers = [{"question_id": i + 1, "option_index": 1} for i in range(5)]
    await client.post("/api/sessions/current/quiz", json={"answers": answers, "optional_note": ""})
    await client.get("/api/sessions/current/recommendations?batch=1")

    points = ["Vraag naar de auto.", "Toon compacte plooien.", "Vergelijk accessoires."]
    with (
        patch("app.routers.session.send_handoff_email", new=AsyncMock()),
        patch("app.routers.session.generate_talking_points", new=AsyncMock(return_value=points)),
    ):
        resp = await client.post("/api/sessions/current/handoff")

    assert resp.status_code == 200
    async with reset_db.execute("SELECT llm_talking_points FROM sessions") as cur:
        row = await cur.fetchone()

    assert json.loads(row["llm_talking_points"]) == points
