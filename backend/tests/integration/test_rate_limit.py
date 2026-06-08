import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
async def client():
    from app.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture(autouse=True)
def clear_rate_limits():
    from app.services.rate_limit import clear_rate_limit_state

    clear_rate_limit_state()
    yield
    clear_rate_limit_state()


async def test_login_rate_limit_blocks_repeated_failures(client):
    for _ in range(10):
        resp = await client.post("/api/auth/login", json={"username": "bad", "password": "bad"})
        assert resp.status_code == 401

    blocked = await client.post("/api/auth/login", json={"username": "bad", "password": "bad"})
    assert blocked.status_code == 429


async def test_session_create_rate_limit_blocks_abuse(client):
    for _ in range(60):
        resp = await client.post("/api/sessions?source=home")
        assert resp.status_code == 200

    blocked = await client.post("/api/sessions?source=home")
    assert blocked.status_code == 429


async def test_staff_basic_auth_failures_are_rate_limited(client):
    headers = basic_auth("staff", "wrong")
    for _ in range(10):
        resp = await client.get("/api/staff/sessions", headers=headers)
        assert resp.status_code == 401

    blocked = await client.get("/api/staff/sessions", headers=headers)
    assert blocked.status_code == 429


async def test_admin_basic_auth_failures_are_rate_limited(client):
    headers = basic_auth("admin", "wrong")
    for _ in range(10):
        resp = await client.get("/api/admin/sessions", headers=headers)
        assert resp.status_code == 401

    blocked = await client.get("/api/admin/sessions", headers=headers)
    assert blocked.status_code == 429


async def test_x_forwarded_for_does_not_bypass_rate_limit(client):
    for i in range(10):
        resp = await client.post(
            "/api/auth/login",
            json={"username": "bad", "password": "bad"},
            headers={"X-Forwarded-For": f"203.0.113.{i}"},
        )
        assert resp.status_code == 401

    blocked = await client.post(
        "/api/auth/login",
        json={"username": "bad", "password": "bad"},
        headers={"X-Forwarded-For": "203.0.113.250"},
    )
    assert blocked.status_code == 429


def basic_auth(username: str, password: str) -> dict[str, str]:
    import base64

    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}
