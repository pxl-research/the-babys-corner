from unittest.mock import patch


async def test_email_retry_marks_failed_after_three_attempts():
    from app.services.email import send_handoff_email

    call_count = 0

    async def fail_send(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise Exception("SMTP failure")

    session = {
        "session_id": "sess1",
        "session_code": "ABC123",
        "source": "home",
        "started_at": "2026-05-05T12:00:00Z",
        "handoff_at": "2026-05-05T12:10:00Z",
        "derived_profile": "A",
        "quiz_answers": [],
        "optional_note": None,
        "shown_products": "[]",
        "stroller_favorites": "[]",
        "accessory_favorites": "[]",
    }

    update_calls = []

    async def mock_update(session_id, status, retry_count):
        update_calls.append((session_id, status, retry_count))

    with patch("app.services.email._send_smtp", new=fail_send):
        with patch("app.services.email._update_email_status", new=mock_update):
            await send_handoff_email(session)

    assert call_count == 3
    assert update_calls[-1][1] == "failed"
    assert update_calls[-1][2] == 3


async def test_email_template_includes_code_timestamp_answers_products_favorites():
    from app.services.email import build_email_html

    session = {
        "session_code": "XYZ789",
        "source": "home",
        "started_at": "2026-05-05T12:00:00Z",
        "handoff_at": "2026-05-05T12:15:00Z",
        "derived_profile": "B",
        "quiz_answers": json_str([{"question_text": "Q1", "option_text": "Opt A"}]),
        "optional_note": "Extra info here",
        "shown_products": json_str([["ST001", "ST002"]]),
        "stroller_favorites": json_str(["ST001"]),
        "accessory_favorites": json_str(["ACC001"]),
    }

    html = build_email_html(session)
    assert "XYZ789" in html
    assert "2026-05-05" in html
    assert "Q1" in html
    assert "Opt A" in html
    assert "ST001" in html
    assert "Extra info here" in html


def json_str(obj) -> str:
    import json
    return json.dumps(obj)
