import pytest
import base64
from httpx import AsyncClient, ASGITransport


def basic_auth(username, password):
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


ADMIN_CREDS = basic_auth("admin", "dev123")
STAFF_CREDS = basic_auth("staff", "dev123")
WRONG_CREDS = basic_auth("admin", "wrongpass")


@pytest.fixture(autouse=True)
def set_admin_creds(monkeypatch):
    import app.config as cfg
    monkeypatch.setattr(cfg.settings, "pxl_admin_username", "admin")
    monkeypatch.setattr(cfg.settings, "pxl_admin_password", "dev123")
    monkeypatch.setattr(cfg.settings, "staff_admin_username", "staff")
    monkeypatch.setattr(cfg.settings, "staff_admin_password", "dev123")


@pytest.fixture
async def client():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def _create_session(client, profile_option=2):
    await client.post("/api/sessions?source=home")
    answers = [{"question_id": i + 1, "option_index": profile_option} for i in range(5)]
    await client.post("/api/sessions/current/quiz", json={"answers": answers, "optional_note": ""})
    await client.get("/api/sessions/current/recommendations?batch=1")
    await client.post("/api/sessions/current/handoff")
    return (await client.get("/api/sessions/current")).json()


async def test_admin_requires_pxl_basic_auth(client):
    resp = await client.get("/api/admin/sessions")
    assert resp.status_code == 401


async def test_admin_wrong_creds_rejected(client):
    resp = await client.get("/api/admin/sessions", headers=WRONG_CREDS)
    assert resp.status_code == 401


async def test_admin_staff_creds_rejected_for_admin(client):
    resp = await client.get("/api/admin/sessions", headers=STAFF_CREDS)
    assert resp.status_code == 401


async def test_admin_filters_by_profile(client):
    await _create_session(client, profile_option=2)  # profile C
    resp = await client.get("/api/admin/sessions?profile=C", headers=ADMIN_CREDS)
    assert resp.status_code == 200
    data = resp.json()
    assert all(s["profile"] == "C" for s in data)


async def test_admin_filters_by_code(client):
    session = await _create_session(client)
    code = session["session_code"]
    resp = await client.get(f"/api/admin/sessions?code={code}", headers=ADMIN_CREDS)
    assert resp.status_code == 200
    assert any(s["session_code"] == code for s in resp.json())


async def test_admin_export_contains_required_columns(client):
    await _create_session(client)
    resp = await client.get("/api/admin/sessions/export", headers=ADMIN_CREDS)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    import openpyxl
    from io import BytesIO
    wb = openpyxl.load_workbook(BytesIO(resp.content))
    ws = wb.active
    headers = [cell.value for cell in ws[1]]
    required = {
        "session_id", "session_code", "source", "status",
        "started_at", "handoff_at", "profile",
        "stroller_favorites", "accessory_favorites", "email_status",
    }
    assert required.issubset(set(headers))
