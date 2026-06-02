from io import BytesIO
import openpyxl


# (export header label, source DB column) — single source of truth so the header
# and row lookups cannot drift (e.g. "profile" header reads "derived_profile").
EXPORT_COLUMNS = [
    ("session_id", "session_id"),
    ("session_code", "session_code"),
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
]


def build_xlsx(rows: list[dict]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sessions"

    ws.append([label for label, _ in EXPORT_COLUMNS])
    for row in rows:
        ws.append([row.get(column, "") for _, column in EXPORT_COLUMNS])

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
