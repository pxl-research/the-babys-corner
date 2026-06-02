"""Shared session fetching and row→schema mapping for the staff and admin routers.

Both routers list sessions and show a session detail with identical row mapping and
`email_failed_warning` logic; only their auth and list filters differ. That shared
shape lives here so it cannot drift between the two.
"""

import json

from app.schemas import StaffSessionDetail, StaffSessionItem


def parse_json_field(value, default):
    """Decode a stored JSON column, returning `default` for null/blank/corrupt values."""
    if not value:
        return default
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def session_item_from_row(row) -> StaffSessionItem:
    return StaffSessionItem(
        session_id=row["session_id"],
        session_code=row["session_code"],
        source=row["source"],
        status=row["status"],
        started_at=row["started_at"],
        handoff_at=row["handoff_at"],
        profile=row["derived_profile"],
        email_status=row["email_status"],
    )


def session_detail_from_row(row) -> StaffSessionDetail:
    row = dict(row)
    return StaffSessionDetail(
        session_id=row["session_id"],
        session_code=row["session_code"],
        source=row["source"],
        status=row["status"],
        started_at=row["started_at"],
        handoff_at=row.get("handoff_at"),
        profile=row.get("derived_profile"),
        quiz_answers=parse_json_field(row.get("quiz_answers"), []),
        optional_note=row.get("optional_note"),
        shown_products=parse_json_field(row.get("shown_products"), []),
        stroller_favorites=parse_json_field(row.get("stroller_favorites"), []),
        accessory_favorites=parse_json_field(row.get("accessory_favorites"), []),
        talking_points=parse_json_field(row.get("llm_talking_points"), None),
        email_status=row.get("email_status"),
        email_failed_warning=row["source"] == "home" and row.get("email_status") == "failed",
    )


async def fetch_session_by_code(db, session_code: str):
    async with db.execute(
        "SELECT * FROM sessions WHERE session_code=? ORDER BY started_at DESC LIMIT 1",
        (session_code,),
    ) as cur:
        return await cur.fetchone()
