import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import settings
from app.database import get_db
from app.schemas import StaffSessionItem, StaffSessionDetail
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


@router.get("/sessions/{session_code}", response_model=StaffSessionDetail)
async def get_admin_session_detail(
    session_code: str,
    _: HTTPBasicCredentials = Depends(verify_admin),
):
    import json

    db = await get_db()
    async with db.execute(
        "SELECT * FROM sessions WHERE session_code=? ORDER BY started_at DESC LIMIT 1",
        (session_code,),
    ) as cur:
        row = await cur.fetchone()

    if not row:
        raise HTTPException(404, detail="Session not found.")

    row = dict(row)
    email_failed_warning = (
        row["source"] == "home" and row.get("email_status") == "failed"
    )

    def _parse(field, default):
        if not field:
            return default
        try:
            return json.loads(field)
        except Exception:
            return default

    return StaffSessionDetail(
        session_id=row["session_id"],
        session_code=row["session_code"],
        source=row["source"],
        status=row["status"],
        started_at=row["started_at"],
        handoff_at=row.get("handoff_at"),
        profile=row.get("derived_profile"),
        quiz_answers=_parse(row.get("quiz_answers"), []),
        optional_note=row.get("optional_note"),
        shown_products=_parse(row.get("shown_products"), []),
        stroller_favorites=_parse(row.get("stroller_favorites"), []),
        accessory_favorites=_parse(row.get("accessory_favorites"), []),
        talking_points=_parse(row.get("llm_talking_points"), None),
        email_status=row.get("email_status"),
        email_failed_warning=email_failed_warning,
    )
