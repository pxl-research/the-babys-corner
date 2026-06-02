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
    answers = [{"question_id": i + 1, "option_index": 0} for i in range(3)]
    await client.post("/api/sessions/current/quiz", json={"answers": answers, "optional_note": ""})


async def test_tag_config_hides_tags(client):
    resp = await client.get("/api/sessions/tag-config")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["questions"]) == 4
    for q in data["questions"]:
        assert "multi" in q
        for opt in q["options"]:
            # Tag mapping must never reach the client.
            assert "tags" not in opt
            assert set(opt.keys()) == {"index", "text"}


async def test_tag_quiz_requires_quiz_first(client):
    await client.post("/api/sessions?source=home")
    resp = await client.post("/api/sessions/current/tag-quiz", json={"answers": []})
    assert resp.status_code == 422


async def test_tag_quiz_empty_returns_all_strollers(client):
    await _session_with_quiz(client)
    resp = await client.post("/api/sessions/current/tag-quiz", json={"answers": []})
    assert resp.status_code == 200
    assert resp.json()["stroller_count"] > 0


async def test_tag_quiz_maps_answers_to_tags(client, reset_db):
    await _session_with_quiz(client)

    # "usage" option 1 → All terrain; option 4 → Twee kinderen (Duo / Tweeling)
    resp = await client.post(
        "/api/sessions/current/tag-quiz",
        json={"answers": [{"question_id": "usage", "option_indices": [1, 4]}]},
    )
    assert resp.status_code == 200

    async with reset_db.execute("SELECT filter_tags, reco_order FROM sessions") as cur:
        row = await cur.fetchone()
    tags = json.loads(row["filter_tags"])
    assert tags == ["All terrain", "Twee kinderen (Duo / Tweeling)"]
    assert len(json.loads(row["reco_order"])) == resp.json()["stroller_count"]


async def test_tag_quiz_ignore_option_yields_no_tags(client, reset_db):
    await _session_with_quiz(client)
    # start_age "ignore" index 2 → no tags
    resp = await client.post(
        "/api/sessions/current/tag-quiz",
        json={"answers": [{"question_id": "start_age", "option_indices": [2]}]},
    )
    assert resp.status_code == 200
    async with reset_db.execute("SELECT filter_tags FROM sessions") as cur:
        row = await cur.fetchone()
    assert json.loads(row["filter_tags"]) == []


async def test_tag_quiz_single_select_rejects_multiple(client):
    await _session_with_quiz(client)
    resp = await client.post(
        "/api/sessions/current/tag-quiz",
        json={"answers": [{"question_id": "start_age", "option_indices": [0, 1]}]},
    )
    assert resp.status_code == 422


async def test_tag_quiz_narrows_recommendations(client):
    await _session_with_quiz(client)
    # fold option 2 → Compact
    await client.post(
        "/api/sessions/current/tag-quiz",
        json={"answers": [{"question_id": "fold", "option_indices": [2]}]},
    )
    resp = await client.get("/api/sessions/current/recommendations?batch=1")
    assert resp.status_code == 200
    products = resp.json()["products"]
    assert all("Compact" in catalog_tags(p["id"]) for p in products)


async def test_tag_quiz_and_used_when_nonempty(client):
    await _session_with_quiz(client)
    # All terrain (usage 1) + 0m+ (start_age 0) — strollers exist with both → AND used.
    resp = await client.post(
        "/api/sessions/current/tag-quiz",
        json={
            "answers": [
                {"question_id": "usage", "option_indices": [1]},
                {"question_id": "start_age", "option_indices": [0]},
            ]
        },
    )
    data = resp.json()
    assert data["match_mode"] == "all"
    assert data["dropped_count"] == 0
    assert data["stroller_count"] == data["strict_count"] > 0


async def test_tag_quiz_recommendations_match_all_tags(client):
    await _session_with_quiz(client)
    await client.post(
        "/api/sessions/current/tag-quiz",
        json={
            "answers": [
                {"question_id": "usage", "option_indices": [1]},
                {"question_id": "start_age", "option_indices": [0]},
            ]
        },
    )
    resp = await client.get("/api/sessions/current/recommendations?batch=1")
    for p in resp.json()["products"]:
        tags = catalog_tags(p["id"])
        assert "All terrain" in tags and "0m+" in tags


async def test_tag_quiz_progressive_drop_on_zero_and(client):
    await _session_with_quiz(client)
    # All terrain (1) + Compact (2): no stroller has both → AND=0 → drop one tag.
    resp = await client.post(
        "/api/sessions/current/tag-quiz",
        json={"answers": [{"question_id": "usage", "option_indices": [1, 2]}]},
    )
    data = resp.json()
    assert data["strict_count"] == 0
    assert data["match_mode"] == "partial"
    assert data["dropped_count"] == 1
    assert data["stroller_count"] > 0

    # Every recommended stroller still carries one of the two requested tags
    # (the kept one), never something unrelated.
    rec = await client.get("/api/sessions/current/recommendations?batch=1")
    for p in rec.json()["products"]:
        tags = catalog_tags(p["id"])
        assert "All terrain" in tags or "Compact" in tags


async def test_tag_count_endpoint(client):
    await _session_with_quiz(client)

    empty = (await client.post("/api/sessions/current/tag-quiz/count", json={"answers": []})).json()
    assert empty["strict_count"] == empty["relaxed_count"] == empty["total_count"] > 0

    # Zero-AND combination: strict 0, relaxed positive.
    combo = (
        await client.post(
            "/api/sessions/current/tag-quiz/count",
            json={"answers": [{"question_id": "usage", "option_indices": [1, 2]}]},
        )
    ).json()
    assert combo["strict_count"] == 0
    assert 0 < combo["relaxed_count"] <= combo["total_count"]


def catalog_tags(stroller_id: str) -> list[str]:
    from app.services.catalog import get_catalog
    s = get_catalog().get_stroller(stroller_id)
    return s.get("tags", []) if s else []
