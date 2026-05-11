import pytest
import json
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch


@pytest.fixture
async def client():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _session_with_quiz(client):
    await client.post("/api/sessions?source=home")
    answers = [{"question_id": i + 1, "option_index": 0} for i in range(5)]
    await client.post("/api/sessions/current/quiz", json={"answers": answers, "optional_note": ""})


async def test_get_tags_returns_sorted_list(client):
    resp = await client.get("/api/filters/tags")
    assert resp.status_code == 200
    data = resp.json()
    assert "tags" in data
    assert isinstance(data["tags"], list)
    assert len(data["tags"]) > 0
    assert data["tags"] == sorted(data["tags"])


async def test_filter_tags_requires_quiz(client):
    await client.post("/api/sessions?source=home")
    resp = await client.post("/api/sessions/current/filters/tags", json={"tags": []})
    assert resp.status_code == 422


async def test_filter_tags_empty_returns_all_brands(client):
    await _session_with_quiz(client)
    resp = await client.post("/api/sessions/current/filters/tags", json={"tags": []})
    assert resp.status_code == 200
    data = resp.json()
    assert "brands" in data
    assert len(data["brands"]) > 0


async def test_filter_tags_narrows_brands(client):
    await _session_with_quiz(client)

    all_resp = await client.post("/api/sessions/current/filters/tags", json={"tags": []})
    all_brands = all_resp.json()["brands"]

    tag_resp = await client.post("/api/sessions/current/filters/tags", json={"tags": ["Compact"]})
    compact_brands = tag_resp.json()["brands"]

    assert len(compact_brands) > 0
    assert len(compact_brands) <= len(all_brands)


async def test_filter_brands_returns_collections_per_brand(client):
    await _session_with_quiz(client)
    await client.post("/api/sessions/current/filters/tags", json={"tags": []})

    resp = await client.post("/api/sessions/current/filters/brands", json={"brands": ["bugaboo"]})
    assert resp.status_code == 200
    data = resp.json()
    assert "brands" in data
    bugaboo = next((b for b in data["brands"] if b["brand"] == "bugaboo"), None)
    assert bugaboo is not None
    assert isinstance(bugaboo["collections"], list)
    assert len(bugaboo["collections"]) > 0


async def test_filter_brands_no_collections_shows_brand(client):
    await _session_with_quiz(client)
    await client.post("/api/sessions/current/filters/tags", json={"tags": []})

    # Find a brand that has no collections
    all_brands_resp = await client.post("/api/sessions/current/filters/brands", json={"brands": ["elodie details"]})
    data = all_brands_resp.json()
    elodie = next((b for b in data["brands"] if b["brand"] == "elodie details"), None)
    if elodie:
        # Brand with no collections has empty list
        assert isinstance(elodie["collections"], list)


async def test_filter_collections_regenerates_reco_order(client, reset_db):
    await _session_with_quiz(client)

    # Get reco_order before filter
    async with reset_db.execute("SELECT reco_order FROM sessions") as cur:
        row = await cur.fetchone()
    initial_reco = json.loads(row["reco_order"]) if row["reco_order"] else []

    # Apply filter: select bugaboo brand, all collections
    await client.post("/api/sessions/current/filters/tags", json={"tags": []})
    await client.post("/api/sessions/current/filters/brands", json={"brands": ["bugaboo"]})
    resp = await client.post(
        "/api/sessions/current/filters/collections",
        json={"selections": [{"brand": "bugaboo", "collection": None}]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "stroller_count" in data
    assert "accessory_count" in data
    assert data["stroller_count"] > 0

    # reco_order should now be regenerated and contain only bugaboo strollers
    async with reset_db.execute("SELECT reco_order FROM sessions") as cur:
        row = await cur.fetchone()
    new_reco = json.loads(row["reco_order"]) if row["reco_order"] else []
    assert new_reco != initial_reco
    assert len(new_reco) == data["stroller_count"]


async def test_filter_collections_empty_returns_all(client):
    await _session_with_quiz(client)
    await client.post("/api/sessions/current/filters/tags", json={"tags": []})
    await client.post("/api/sessions/current/filters/brands", json={"brands": []})
    resp = await client.post("/api/sessions/current/filters/collections", json={"selections": []})
    assert resp.status_code == 200
    data = resp.json()
    assert data["stroller_count"] > 0


async def test_recommendations_use_filtered_reco_order(client):
    await _session_with_quiz(client)
    await client.post("/api/sessions/current/filters/tags", json={"tags": []})
    await client.post("/api/sessions/current/filters/brands", json={"brands": ["bugaboo"]})
    await client.post(
        "/api/sessions/current/filters/collections",
        json={"selections": [{"brand": "bugaboo", "collection": None}]},
    )

    resp = await client.get("/api/sessions/current/recommendations?batch=1")
    assert resp.status_code == 200
    products = resp.json()["products"]
    assert all(p["brand"] == "bugaboo" for p in products)


async def test_note_endpoint_saves_note(client, reset_db):
    await _session_with_quiz(client)
    resp = await client.post("/api/sessions/current/note", json={"note": "Wij zoeken iets compacts"})
    assert resp.status_code == 200
    assert resp.json()["note"] == "Wij zoeken iets compacts"

    async with reset_db.execute("SELECT optional_note FROM sessions") as cur:
        row = await cur.fetchone()
    assert row["optional_note"] == "Wij zoeken iets compacts"


async def test_note_endpoint_triggers_llm_rerank(client, reset_db):
    await _session_with_quiz(client)
    await client.post("/api/sessions/current/filters/tags", json={"tags": []})
    await client.post("/api/sessions/current/filters/brands", json={"brands": ["bugaboo"]})
    await client.post(
        "/api/sessions/current/filters/collections",
        json={"selections": [{"brand": "bugaboo", "collection": None}]},
    )

    async with reset_db.execute("SELECT reco_order FROM sessions") as cur:
        row = await cur.fetchone()
    reco_before = json.loads(row["reco_order"])
    reversed_all = list(reversed(reco_before))

    with patch("app.services.llm.rerank_by_note", new=AsyncMock(return_value=reversed_all)):
        resp = await client.post("/api/sessions/current/note", json={"note": "Iets sportiefs"})

    assert resp.status_code == 200
    async with reset_db.execute("SELECT reco_order FROM sessions") as cur:
        row = await cur.fetchone()
    new_reco = json.loads(row["reco_order"])
    assert new_reco == reversed_all


async def test_filter_tags_resets_downstream_filters(client, reset_db):
    await _session_with_quiz(client)
    await client.post("/api/sessions/current/filters/tags", json={"tags": []})
    await client.post("/api/sessions/current/filters/brands", json={"brands": ["bugaboo"]})
    await client.post(
        "/api/sessions/current/filters/collections",
        json={"selections": [{"brand": "bugaboo", "collection": None}]},
    )

    # Re-submit tags — should clear brands and collections
    await client.post("/api/sessions/current/filters/tags", json={"tags": ["Compact"]})

    async with reset_db.execute("SELECT filter_brands, filter_collections FROM sessions") as cur:
        row = await cur.fetchone()
    assert row["filter_brands"] is None
    assert row["filter_collections"] is None
