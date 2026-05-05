import json
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from app.config import settings
from app.database import get_db
from app.schemas import StaffSessionItem, StaffSessionDetail

router = APIRouter(prefix="/api/staff", tags=["staff"])
security = HTTPBasic()


def verify_staff(credentials: HTTPBasicCredentials = Depends(security)):
    ok = (
        secrets.compare_digest(credentials.username, settings.staff_admin_username)
        and secrets.compare_digest(credentials.password, settings.staff_admin_password)
    )
    if not ok:
        raise HTTPException(401, headers={"WWW-Authenticate": "Basic"})
    return credentials


def _parse_json_field(value, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


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


@router.get("/sessions/{session_code}", response_model=StaffSessionDetail)
async def get_session_by_code(
    session_code: str,
    _: HTTPBasicCredentials = Depends(verify_staff),
):
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

    talking_points = _parse_json_field(row.get("llm_talking_points"), None)

    return StaffSessionDetail(
        session_id=row["session_id"],
        session_code=row["session_code"],
        source=row["source"],
        status=row["status"],
        started_at=row["started_at"],
        handoff_at=row.get("handoff_at"),
        profile=row.get("derived_profile"),
        quiz_answers=_parse_json_field(row.get("quiz_answers"), []),
        optional_note=row.get("optional_note"),
        shown_products=_parse_json_field(row.get("shown_products"), []),
        stroller_favorites=_parse_json_field(row.get("stroller_favorites"), []),
        accessory_favorites=_parse_json_field(row.get("accessory_favorites"), []),
        talking_points=talking_points,
        email_status=row.get("email_status"),
        email_failed_warning=email_failed_warning,
    )
