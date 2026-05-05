import aiosqlite
import os
from app.config import settings

_db: aiosqlite.Connection | None = None

CREATE_SESSIONS_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id       TEXT PRIMARY KEY,
    session_code     TEXT NOT NULL,
    source           TEXT NOT NULL DEFAULT 'home',
    status           TEXT NOT NULL DEFAULT 'active',
    started_at       TEXT NOT NULL,
    quiz_submitted_at TEXT,
    first_reco_at    TEXT,
    handoff_at       TEXT,
    quiz_answers     TEXT,
    optional_note    TEXT,
    derived_profile  TEXT,
    shown_products   TEXT,
    stroller_favorites TEXT,
    accessory_favorites TEXT,
    reco_order       TEXT,
    extra_reco_order TEXT,
    favorites_adaptation_active INTEGER DEFAULT 0,
    email_status     TEXT DEFAULT 'not_sent',
    email_retry_count INTEGER DEFAULT 0,
    email_last_attempt TEXT,
    llm_key_features TEXT,
    llm_talking_points TEXT,
    llm_ranking_output TEXT,
    llm_similarity_output TEXT
);
"""


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        os.makedirs(os.path.dirname(settings.database_path), exist_ok=True)
        _db = await aiosqlite.connect(settings.database_path)
        _db.row_factory = aiosqlite.Row
    return _db


async def init_db():
    db = await get_db()
    await db.execute(CREATE_SESSIONS_SQL)
    await db.commit()
