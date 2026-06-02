import secrets
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import settings
from app.database import get_db
from app.schemas import StaffSessionItem, StaffSessionDetail
from app.services.auth import verify_token
from app.services.session_service import (
    fetch_session_by_code,
    session_detail_from_row,
    session_item_from_row,
)

router = APIRouter(prefix="/api/staff", tags=["staff"])
security = HTTPBasic(auto_error=False)


def verify_staff(
    auth_token: Optional[str] = Cookie(default=None),
    credentials: Optional[HTTPBasicCredentials] = Depends(security),
):
    # Cookie session (preferred) — the admin role also satisfies staff access.
    if verify_token(auth_token) in ("staff", "admin"):
        return
    # Backwards-compatible HTTP Basic.
    if (
        credentials
        and secrets.compare_digest(credentials.username, settings.staff_admin_username)
        and secrets.compare_digest(credentials.password, settings.staff_admin_password)
    ):
        return
    raise HTTPException(401, headers={"WWW-Authenticate": "Basic"})


@router.get("/sessions", response_model=list[StaffSessionItem])
async def list_sessions(
    code: Optional[str] = None,
    date: Optional[str] = None,
    source: Optional[str] = None,
    _: HTTPBasicCredentials = Depends(verify_staff),
):
    db = await get_db()
    conditions = []
    params = []

    if code:
        conditions.append("session_code LIKE ?")
        params.append(f"%{code}%")
    if date:
        conditions.append("started_at LIKE ?")
        params.append(f"{date}%")
    if source:
        conditions.append("source = ?")
        params.append(source)

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"SELECT * FROM sessions {where} ORDER BY started_at DESC LIMIT 25"

    async with db.execute(query, params) as cur:
        rows = await cur.fetchall()

    return [session_item_from_row(row) for row in rows]


@router.get("/sessions/{session_code}", response_model=StaffSessionDetail)
async def get_session_by_code(
    session_code: str,
    _: HTTPBasicCredentials = Depends(verify_staff),
):
    db = await get_db()
    row = await fetch_session_by_code(db, session_code)
    if not row:
        raise HTTPException(404, detail="Session not found.")
    return session_detail_from_row(row)
