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
    reco_tiers       TEXT,
    extra_reco_order TEXT,
    favorites_adaptation_active INTEGER DEFAULT 0,
    email_status     TEXT DEFAULT 'not_sent',
    email_retry_count INTEGER DEFAULT 0,
    email_last_attempt TEXT,
    llm_key_features TEXT,
    llm_talking_points TEXT,
    llm_ranking_output TEXT,
    llm_similarity_output TEXT,
    filter_tags TEXT,
    filter_brands TEXT,
    filter_collections TEXT,
    contact_name TEXT,
    contact_surname TEXT,
    contact_email TEXT
);
"""


async def get_db() -> aiosqlite.Connection:
    global _db
    if _db is None:
        os.makedirs(os.path.dirname(settings.database_path), exist_ok=True)
        conn = await aiosqlite.connect(settings.database_path)
        conn.row_factory = aiosqlite.Row
        _db = conn
    return _db


_MIGRATION_COLUMNS = [
    "filter_tags TEXT",
    "filter_brands TEXT",
    "filter_collections TEXT",
    "reco_tiers TEXT",
    "contact_name TEXT",
    "contact_surname TEXT",
    "contact_email TEXT",
]


async def init_db():
    db = await get_db()
    await db.execute(CREATE_SESSIONS_SQL)
    for col_def in _MIGRATION_COLUMNS:
        try:
            await db.execute(f"ALTER TABLE sessions ADD COLUMN {col_def}")
        except aiosqlite.OperationalError as e:
            # Only "already added" is expected; surface any real migration failure.
            if "duplicate column name" not in str(e):
                raise
    # Enforce session-code uniqueness so staff lookups can never be ambiguous.
    await db.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_sessions_session_code ON sessions(session_code)")
    await db.commit()
