from io import BytesIO
import json
import openpyxl

from app.content import category_labels


# (export header label, source DB column) — single source of truth so the header
# and row lookups cannot drift (e.g. "profile" header reads "derived_profile").
EXPORT_COLUMNS = [
    ("session_id", "session_id"),
    ("session_code", "session_code"),
    ("contact_name", "contact_name"),
    ("contact_surname", "contact_surname"),
    ("contact_email", "contact_email"),
    ("source", "source"),
    ("status", "status"),
    ("started_at", "started_at"),
    ("quiz_submitted_at", "quiz_submitted_at"),
    ("first_reco_at", "first_reco_at"),
    ("handoff_at", "handoff_at"),
    ("profile", "derived_profile"),
    ("optional_note", "optional_note"),
    ("quiz_answers", "quiz_answers"),
    ("stroller_favorites", "stroller_favorites"),
    ("accessory_favorites", "accessory_favorites"),
    ("llm_key_features", "llm_key_features"),
    ("llm_talking_points", "llm_talking_points"),
    ("email_status", "email_status"),
    ("selected_categories", "selected_categories"),
]


def _resolve_export_rows(rows: list[dict]) -> list[dict]:
    """Resolve selected_categories ids → human-readable labels for export."""
    out = []
    for row in rows:
        row = dict(row)
        raw = row.get("selected_categories")
        if raw:
            try:
                ids = json.loads(raw)
                row["selected_categories"] = ", ".join(category_labels(ids))
            except (json.JSONDecodeError, TypeError):
                pass
        out.append(row)
    return out


def build_xlsx(rows: list[dict]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sessions"

    ws.append([label for label, _ in EXPORT_COLUMNS])
    for row in _resolve_export_rows(rows):
        ws.append([row.get(column, "") for _, column in EXPORT_COLUMNS])

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
