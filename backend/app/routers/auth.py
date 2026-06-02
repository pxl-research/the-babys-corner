import secrets
from typing import Optional

from fastapi import APIRouter, Cookie, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.config import settings
from app.services.auth import COOKIE_NAME, DEFAULT_TTL_SECONDS, issue_token, verify_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


def _role_for(username: str, password: str) -> Optional[str]:
    if secrets.compare_digest(username, settings.pxl_admin_username) and secrets.compare_digest(
        password, settings.pxl_admin_password
    ):
        return "admin"
    if secrets.compare_digest(username, settings.staff_admin_username) and secrets.compare_digest(
        password, settings.staff_admin_password
    ):
        return "staff"
    return None


@router.post("/login")
async def login(body: LoginRequest):
    role = _role_for(body.username, body.password)
    if not role:
        raise HTTPException(401, detail="Invalid credentials.")
    resp = JSONResponse(content={"role": role})
    resp.set_cookie(
        key=COOKIE_NAME,
        value=issue_token(role),
        httponly=True,
        samesite="lax",
        secure=settings.session_cookie_secure,
        max_age=DEFAULT_TTL_SECONDS,
        path="/",
    )
    return resp


@router.post("/logout")
async def logout():
    resp = JSONResponse(content={"status": "logged_out"})
    resp.delete_cookie(key=COOKIE_NAME, path="/")
    return resp


@router.get("/me")
async def me(auth_token: Optional[str] = Cookie(default=None)):
    role = verify_token(auth_token)
    if not role:
        raise HTTPException(401, detail="Not authenticated.")
    return {"role": role}
