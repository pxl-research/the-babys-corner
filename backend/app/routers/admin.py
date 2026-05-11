import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import settings
from app.database import get_db
from app.schemas import StaffSessionItem
from app.services.export import build_xlsx

router = APIRouter(prefix="/api/admin", tags=["admin"])
security = HTTPBasic()


def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    ok = (
        secrets.compare_digest(credentials.username, settings.pxl_admin_username)
        and secrets.compare_digest(credentials.password, settings.pxl_admin_password)
    )
    if not ok:
        raise HTTPException(401, headers={"WWW-Authenticate": "Basic"})
    return credentials


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

    return [
        StaffSessionItem(
            session_id=row["session_id"],
            session_code=row["session_code"],
            source=row["source"],
            status=row["status"],
            started_at=row["started_at"],
            handoff_at=row["handoff_at"],
            profile=row["derived_profile"],
            email_status=row["email_status"],
        )
        for row in rows
    ]


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
