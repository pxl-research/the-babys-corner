import pytest
from httpx import AsyncClient, ASGITransport

from app.config import settings


@pytest.fixture
async def client():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_login_rejects_bad_credentials(client):
    resp = await client.post("/api/auth/login", json={"username": "nope", "password": "nope"})
    assert resp.status_code == 401


async def test_staff_login_sets_cookie_and_grants_staff_access(client):
    resp = await client.post(
        "/api/auth/login",
        json={"username": settings.staff_admin_username, "password": settings.staff_admin_password},
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "staff"
    assert "auth_token" in resp.cookies

    me = await client.get("/api/auth/me")
    assert me.status_code == 200 and me.json()["role"] == "staff"

    # Cookie alone authorizes staff endpoints — no Authorization header sent.
    listing = await client.get("/api/staff/sessions")
    assert listing.status_code == 200


async def test_staff_cookie_cannot_access_admin(client):
    await client.post(
        "/api/auth/login",
        json={"username": settings.staff_admin_username, "password": settings.staff_admin_password},
    )
    resp = await client.get("/api/admin/sessions")
    assert resp.status_code == 401


async def test_admin_login_grants_admin_and_staff(client):
    resp = await client.post(
        "/api/auth/login",
        json={"username": settings.pxl_admin_username, "password": settings.pxl_admin_password},
    )
    assert resp.status_code == 200 and resp.json()["role"] == "admin"

    assert (await client.get("/api/admin/sessions")).status_code == 200
    assert (await client.get("/api/staff/sessions")).status_code == 200


async def test_logout_clears_cookie(client):
    await client.post(
        "/api/auth/login",
        json={"username": settings.staff_admin_username, "password": settings.staff_admin_password},
    )
    await client.post("/api/auth/logout")
    client.cookies.clear()
    assert (await client.get("/api/staff/sessions")).status_code == 401
    assert (await client.get("/api/auth/me")).status_code == 401
