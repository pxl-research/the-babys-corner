import json
from io import BytesIO
import openpyxl


COLUMNS = [
    "session_id", "session_code", "source", "status",
    "started_at", "quiz_submitted_at", "first_reco_at", "handoff_at",
    "profile", "optional_note",
    "quiz_answers", "stroller_favorites", "accessory_favorites",
    "llm_key_features", "llm_talking_points", "email_status",
]


def build_xlsx(rows: list[dict]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sessions"

    ws.append(COLUMNS)

    for row in rows:
        ws.append([
            row.get("session_id", ""),
            row.get("session_code", ""),
            row.get("source", ""),
            row.get("status", ""),
            row.get("started_at", ""),
            row.get("quiz_submitted_at", ""),
            row.get("first_reco_at", ""),
            row.get("handoff_at", ""),
            row.get("derived_profile", ""),
            row.get("optional_note", ""),
            row.get("quiz_answers", ""),
            row.get("stroller_favorites", ""),
            row.get("accessory_favorites", ""),
            row.get("llm_key_features", ""),
            row.get("llm_talking_points", ""),
            row.get("email_status", ""),
        ])

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()
