import json
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
async def client():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _session_with_quiz(client):
    await client.post("/api/sessions?source=home")
    answers = [{"question_id": i + 1, "option_index": 0} for i in range(2)]
    await client.post("/api/sessions/current/quiz", json={"answers": answers, "optional_note": ""})


async def test_select_category_requires_session(client):
    resp = await client.post("/api/sessions/current/category", json={"category_id": "strollers"})
    assert resp.status_code == 401


async def test_select_valid_ai_category(client):
    await client.post("/api/sessions?source=home")
    resp = await client.post("/api/sessions/current/category", json={"category_id": "strollers"})
    assert resp.status_code == 200
    assert resp.json()["selected_categories"] == ["strollers"]


async def test_select_unknown_category_returns_422(client):
    await client.post("/api/sessions?source=home")
    resp = await client.post("/api/sessions/current/category", json={"category_id": "not_a_category"})
    assert resp.status_code == 422


async def test_select_soon_category_returns_422(client):
    await client.post("/api/sessions?source=home")
    resp = await client.post("/api/sessions/current/category", json={"category_id": "car_seats"})
    assert resp.status_code == 422


async def test_select_category_deduplicates_on_repeat(client):
    await client.post("/api/sessions?source=home")
    await client.post("/api/sessions/current/category", json={"category_id": "strollers"})
    resp = await client.post("/api/sessions/current/category", json={"category_id": "strollers"})
    assert resp.status_code == 200
    assert resp.json()["selected_categories"] == ["strollers"]


async def test_current_session_exposes_selected_categories(client):
    await client.post("/api/sessions?source=home")
    await client.post("/api/sessions/current/category", json={"category_id": "strollers"})
    resp = await client.get("/api/sessions/current")
    assert resp.status_code == 200
    assert resp.json()["selected_categories"] == ["strollers"]


# ── T3: tag-quiz re-submit resets pagination state ───────────────────────────

async def test_tag_quiz_resubmit_resets_shown_products(client, reset_db):
    await _session_with_quiz(client)

    # First tag-quiz + fetch batch 1 (records shown_products)
    await client.post("/api/sessions/current/tag-quiz", json={"answers": []})
    batch1 = (await client.get("/api/sessions/current/recommendations?batch=1")).json()
    assert len(batch1["products"]) > 0

    # Verify shown_products is non-empty after batch 1
    async with reset_db.execute("SELECT shown_products FROM sessions") as cur:
        row = await cur.fetchone()
    assert json.loads(row["shown_products"]) != []

    # Re-submit tag quiz (category re-entry)
    await client.post("/api/sessions/current/tag-quiz", json={"answers": []})

    async with reset_db.execute("SELECT shown_products, favorites_adaptation_active FROM sessions") as cur:
        row = await cur.fetchone()
    assert json.loads(row["shown_products"]) == []
    assert row["favorites_adaptation_active"] == 0


async def test_tag_quiz_resubmit_batch1_returns_full_grid(client):
    await _session_with_quiz(client)

    # First run
    await client.post("/api/sessions/current/tag-quiz", json={"answers": []})
    first_batch = (await client.get("/api/sessions/current/recommendations?batch=1")).json()
    assert len(first_batch["products"]) > 0

    # Re-entry: re-submit tag quiz (resets shown_products), then fetch batch 1 again.
    # Batch 1 must return a full grid — not empty due to dedup against prior shown batches.
    await client.post("/api/sessions/current/tag-quiz", json={"answers": []})
    second_batch = (await client.get("/api/sessions/current/recommendations?batch=1")).json()
    assert len(second_batch["products"]) == len(first_batch["products"])
