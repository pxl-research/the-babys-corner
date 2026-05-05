import pytest
import aiosqlite
from unittest.mock import patch, AsyncMock
from app.database import CREATE_SESSIONS_SQL


@pytest.fixture(autouse=True)
async def reset_db(tmp_path):
    """Each test gets a fresh SQLite DB; patches get_db everywhere."""
    db_path = str(tmp_path / "test.db")
    conn = await aiosqlite.connect(db_path)
    conn.row_factory = aiosqlite.Row
    await conn.execute(CREATE_SESSIONS_SQL)
    await conn.commit()

    async def mock_get_db():
        return conn

    patches = [
        patch("app.database.get_db", mock_get_db),
        patch("app.routers.session.get_db", mock_get_db),
        patch("app.routers.staff.get_db", mock_get_db),
        patch("app.routers.admin.get_db", mock_get_db),
        patch("app.services.email._update_email_status", AsyncMock()),
    ]

    for p in patches:
        p.start()

    yield conn

    for p in patches:
        p.stop()

    await conn.close()
