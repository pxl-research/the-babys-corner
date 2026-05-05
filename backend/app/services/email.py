import asyncio
import json
import logging
from datetime import datetime, timezone

from app.config import settings

logger = logging.getLogger(__name__)

PROFILE_LABELS = {
    "A": "Minimalist",
    "B": "Ontdekker",
    "C": "Planner",
}


def build_email_html(session: dict) -> str:
    code = session.get("session_code", "")
    source = session.get("source", "")
    started_at = session.get("started_at", "")
    handoff_at = session.get("handoff_at", "")
    profile = session.get("derived_profile", "")
    profile_label = PROFILE_LABELS.get(profile, profile)
    optional_note = session.get("optional_note") or ""

    try:
        quiz_answers = json.loads(session.get("quiz_answers") or "[]")
    except Exception:
        quiz_answers = []

    try:
        shown = json.loads(session.get("shown_products") or "[]")
        shown_flat = [id_ for batch in shown for id_ in batch]
    except Exception:
        shown_flat = []

    try:
        stroller_favs = json.loads(session.get("stroller_favorites") or "[]")
    except Exception:
        stroller_favs = []

    try:
        accessory_favs = json.loads(session.get("accessory_favorites") or "[]")
    except Exception:
        accessory_favs = []

    answers_html = "".join(
        f"<li><b>{a.get('question_text', '')}</b>: {a.get('option_text', '')}</li>"
        for a in quiz_answers
    )
    shown_html = "".join(f"<li>{id_}</li>" for id_ in shown_flat)
    stroller_html = "".join(f"<li>{id_}</li>" for id_ in stroller_favs)
    acc_html = "".join(f"<li>{id_}</li>" for id_ in accessory_favs)
    note_html = f"<p><b>Extra info:</b> {optional_note}</p>" if optional_note else ""

    return f"""<!DOCTYPE html>
<html>
<body>
<h1>Sessiesamenvatting — The Baby's Corner</h1>
<p><b>Sessiecode:</b> {code}</p>
<p><b>Bron:</b> {source}</p>
<p><b>Gestart:</b> {started_at}</p>
<p><b>Handoff:</b> {handoff_at}</p>
<p><b>Profiel:</b> {profile_label} ({profile})</p>
{note_html}
<h2>Antwoorden</h2><ul>{answers_html}</ul>
<h2>Bekeken producten</h2><ul>{shown_html}</ul>
<h2>Favorieten — Kinderwagens</h2><ul>{stroller_html}</ul>
<h2>Favorieten — Accessoires</h2><ul>{acc_html}</ul>
</body>
</html>"""


async def _send_smtp(html: str, subject: str):
    import aiosmtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.smtp_username
    msg["To"] = settings.staff_email
    msg.attach(MIMEText(html, "html", "utf-8"))

    await aiosmtplib.send(
        msg,
        hostname=settings.smtp_host,
        port=settings.smtp_port,
        username=settings.smtp_username,
        password=settings.smtp_password,
        start_tls=True,
    )


async def _update_email_status(session_id: str, status: str, retry_count: int):
    from app.database import get_db
    now = datetime.now(timezone.utc).isoformat()
    db = await get_db()
    await db.execute(
        "UPDATE sessions SET email_status=?, email_retry_count=?, email_last_attempt=? WHERE session_id=?",
        (status, retry_count, now, session_id),
    )
    await db.commit()


async def send_handoff_email(session: dict):
    session_id = session.get("session_id", "")
    code = session.get("session_code", "")
    html = build_email_html(session)
    subject = f"The Baby's Corner — Sessie {code}"

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        try:
            await _send_smtp(html, subject)
            await _update_email_status(session_id, "sent", attempt)
            return
        except Exception as e:
            logger.warning("Email attempt %d failed: %s", attempt, e)
            if attempt < max_attempts:
                await asyncio.sleep(2 ** (attempt - 1))

    await _update_email_status(session_id, "failed", max_attempts)
