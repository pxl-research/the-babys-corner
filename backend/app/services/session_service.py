"""Shared session fetching and row→schema mapping for the staff and admin routers.

Both routers list sessions and show a session detail with identical row mapping and
`email_failed_warning` logic; only their auth and list filters differ. That shared
shape lives here so it cannot drift between the two.
"""

import json

from app.schemas import NamedItem, StaffSessionDetail, StaffSessionItem


def parse_json_field(value, default):
    """Decode a stored JSON column, returning `default` for null/blank/corrupt values."""
    if not value:
        return default
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default


def _named(item: dict) -> NamedItem:
    return NamedItem(
        id=item["id"],
        name=item["name"],
        brand=item["brand"],
        image_url=item.get("image_url", ""),
        price=item.get("price"),
    )


def resolve_strollers(ids, catalog) -> list[NamedItem]:
    """Map stroller IDs to {id, name, brand}; unknown IDs are dropped, order preserved."""
    return [_named(s) for id_ in ids if (s := catalog.get_stroller(id_))]


def resolve_accessories(ids, catalog) -> list[NamedItem]:
    """Map accessory IDs to {id, name, brand}; unknown IDs are dropped, order preserved."""
    return [_named(a) for id_ in ids if (a := catalog.get_accessory(id_))]


def resolve_stroller_batches(batches, catalog) -> list[list[NamedItem]]:
    return [resolve_strollers(batch, catalog) for batch in batches]


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


def session_detail_from_row(row, catalog=None) -> StaffSessionDetail:
    row = dict(row)
    shown = parse_json_field(row.get("shown_products"), [])
    stroller_favs = parse_json_field(row.get("stroller_favorites"), [])
    accessory_favs = parse_json_field(row.get("accessory_favorites"), [])
    # Resolve IDs to names so staff read products, not codes. Falls back to empty
    # named lists when no catalog is supplied (the raw ID lists are always present).
    shown_named = resolve_stroller_batches(shown, catalog) if catalog else []
    stroller_named = resolve_strollers(stroller_favs, catalog) if catalog else []
    accessory_named = resolve_accessories(accessory_favs, catalog) if catalog else []
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
        shown_products=shown,
        stroller_favorites=stroller_favs,
        accessory_favorites=accessory_favs,
        shown_products_named=shown_named,
        stroller_favorites_named=stroller_named,
        accessory_favorites_named=accessory_named,
        talking_points=parse_json_field(row.get("llm_talking_points"), None),
        email_status=row.get("email_status"),
        email_failed_warning=row["source"] == "home" and row.get("email_status") == "failed",
        contact_name=row.get("contact_name"),
        contact_surname=row.get("contact_surname"),
        contact_email=row.get("contact_email"),
    )


async def fetch_session_by_code(db, session_code: str):
    async with db.execute(
        "SELECT * FROM sessions WHERE session_code=? ORDER BY started_at DESC LIMIT 1",
        (session_code,),
    ) as cur:
        return await cur.fetchone()
