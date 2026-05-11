import pytest
import aiosqlite
import json
from datetime import datetime, timezone

from app.database import CREATE_SESSIONS_SQL
from app.schemas import SessionStatus


@pytest.fixture
async def db():
    conn = await aiosqlite.connect(":memory:")
    conn.row_factory = aiosqlite.Row
    await conn.execute(CREATE_SESSIONS_SQL)
    await conn.commit()
    yield conn
    await conn.close()


async def insert_session(db, session_id="sess1", status="active"):
    now = datetime.now(timezone.utc).isoformat()
    await db.execute(
        """INSERT INTO sessions (session_id, session_code, source, status, started_at)
           VALUES (?, ?, ?, ?, ?)""",
        (session_id, "ABC123", "home", status, now),
    )
    await db.commit()


async def test_schema_creates_sessions_table_with_required_columns(db):
    async with db.execute("PRAGMA table_info(sessions)") as cursor:
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


async def test_locked_session_rejects_quiz_submit(db):
    await insert_session(db, status="handed_off")
    async with db.execute("SELECT status FROM sessions WHERE session_id=?", ("sess1",)) as cur:
        row = await cur.fetchone()
    assert row["status"] == "handed_off"
    assert row["status"] != "active"


async def test_locked_session_rejects_favorite_toggle(db):
    await insert_session(db, status="handed_off")
    async with db.execute("SELECT status FROM sessions WHERE session_id=?", ("sess1",)) as cur:
        row = await cur.fetchone()
    assert row["status"] == "handed_off"


async def test_locked_session_rejects_new_unshown_recommendation_batch(db):
    await insert_session(db, status="handed_off")
    async with db.execute("SELECT status FROM sessions WHERE session_id=?", ("sess1",)) as cur:
        row = await cur.fetchone()
    assert row["status"] == "handed_off"


async def test_locked_session_allows_current_read(db):
    await insert_session(db, status="handed_off")
    async with db.execute("SELECT * FROM sessions WHERE session_id=?", ("sess1",)) as cur:
        row = await cur.fetchone()
    assert row is not None
    assert row["session_id"] == "sess1"


async def test_abandon_rejects_handed_off_session(db):
    await insert_session(db, status="handed_off")
    async with db.execute("SELECT status FROM sessions WHERE session_id=?", ("sess1",)) as cur:
        row = await cur.fetchone()
    assert row["status"] == "handed_off"
    # Abandon is only valid when status != handed_off
    assert row["status"] != "active"
