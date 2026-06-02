import secrets
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, HTTPException
from fastapi.responses import Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import settings
from app.database import get_db
from app.schemas import StaffSessionItem, StaffSessionDetail
from app.services.auth import verify_token
from app.services.export import build_xlsx
from app.services.session_service import (
    fetch_session_by_code,
    session_detail_from_row,
    session_item_from_row,
)

router = APIRouter(prefix="/api/admin", tags=["admin"])
security = HTTPBasic(auto_error=False)


def verify_admin(
    auth_token: Optional[str] = Cookie(default=None),
    credentials: Optional[HTTPBasicCredentials] = Depends(security),
):
    # Cookie session (preferred) — admin only.
    if verify_token(auth_token) == "admin":
        return
    # Backwards-compatible HTTP Basic.
    if (
        credentials
        and secrets.compare_digest(credentials.username, settings.pxl_admin_username)
        and secrets.compare_digest(credentials.password, settings.pxl_admin_password)
    ):
        return
    raise HTTPException(401, headers={"WWW-Authenticate": "Basic"})


@router.get("/sessions", response_model=list[StaffSessionItem])
async def list_sessions(
    profile: Optional[str] = None,
    code: Optional[str] = None,
    _: HTTPBasicCredentials = Depends(verify_admin),
):
    db = await get_db()
    conditions = []
    params = []

    if profile:
        conditions.append("derived_profile = ?")
        params.append(profile)
    if code:
        conditions.append("session_code LIKE ?")
        params.append(f"%{code}%")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"SELECT * FROM sessions {where} ORDER BY started_at DESC"

    async with db.execute(query, params) as cur:
        rows = await cur.fetchall()

    return [session_item_from_row(row) for row in rows]


@router.get("/sessions/export")
async def export_sessions(_: HTTPBasicCredentials = Depends(verify_admin)):
    db = await get_db()
    async with db.execute("SELECT * FROM sessions ORDER BY started_at DESC") as cur:
        rows = [dict(row) async for row in cur]

    xlsx_bytes = build_xlsx(rows)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=sessions.xlsx"},
    )


@router.get("/sessions/{session_code}", response_model=StaffSessionDetail)
async def get_admin_session_detail(
    session_code: str,
    _: HTTPBasicCredentials = Depends(verify_admin),
):
    db = await get_db()
    row = await fetch_session_by_code(db, session_code)
    if not row:
        raise HTTPException(404, detail="Session not found.")
    return session_detail_from_row(row)
