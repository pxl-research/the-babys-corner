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
            with patch("app.services.email.asyncio.sleep", new=noop_sleep):
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


def test_email_template_escapes_user_controlled_html():
    from app.services.email import build_email_html

    session = {
        "session_code": 'CODE<img src=x onerror="alert(1)">',
        "source": 'home<a href="https://evil.example">source</a>',
        "started_at": '2026-05-05T12:00:00Z<img src=x onerror="alert(2)">',
        "handoff_at": '2026-05-05T12:15:00Z<a href="https://evil.example">time</a>',
        "derived_profile": '<img src=x onerror="alert(3)">',
        "quiz_answers": json_str(
            [
                {
                    "question_text": '<b>Question</b><img src=x onerror="alert(4)">',
                    "option_text": '<a href="https://evil.example">Option</a>',
                }
            ]
        ),
        "optional_note": '<img src=x onerror="alert(5)"><a href="https://evil.example">note</a>',
        "shown_products": json_str(
            [['ST001<img src=x onerror="alert(6)">', '<a href="https://evil.example">ST002</a>']]
        ),
        "stroller_favorites": json_str(['<b>Question</b><img src=x onerror="alert(7)">']),
        "accessory_favorites": json_str(['ACC001<a href="https://evil.example">fav</a>']),
    }

    html = build_email_html(session)

    assert "<img" not in html
    assert "<a" not in html
    assert "<b>Question</b>" not in html
    assert 'CODE&lt;img src=x onerror=&quot;alert(1)&quot;&gt;' in html
    assert 'home&lt;a href=&quot;https://evil.example&quot;&gt;source&lt;/a&gt;' in html
    assert '&lt;b&gt;Question&lt;/b&gt;&lt;img src=x onerror=&quot;alert(4)&quot;&gt;' in html
    assert '&lt;a href=&quot;https://evil.example&quot;&gt;Option&lt;/a&gt;' in html
    assert '&lt;img src=x onerror=&quot;alert(5)&quot;&gt;' in html
    assert 'ST001&lt;img src=x onerror=&quot;alert(6)&quot;&gt;' in html
    assert '&lt;b&gt;Question&lt;/b&gt;&lt;img src=x onerror=&quot;alert(7)&quot;&gt;' in html
    assert 'ACC001&lt;a href=&quot;https://evil.example&quot;&gt;fav&lt;/a&gt;' in html


def test_email_template_tolerates_malformed_json_shapes():
    from app.services.email import build_email_html

    session = {
        "session_code": "XYZ789",
        "source": "home",
        "started_at": "2026-05-05T12:00:00Z",
        "handoff_at": "2026-05-05T12:15:00Z",
        "derived_profile": "B",
        "quiz_answers": json_str([None, "bad", {"question_text": "Q1", "option_text": "Opt A"}]),
        "optional_note": "",
        "shown_products": json_str(["ST001", "ST002"]),
        "stroller_favorites": json_str(["ST003"]),
        "accessory_favorites": json_str(["ACC001"]),
    }

    html = build_email_html(session)

    assert "Q1" in html
    assert "Opt A" in html
    assert "ST001" in html
    assert "ST002" in html


def test_email_template_tolerates_scalar_json_values():
    from app.services.email import build_email_html

    session = {
        "session_code": "XYZ789",
        "source": "home",
        "started_at": "2026-05-05T12:00:00Z",
        "handoff_at": "2026-05-05T12:15:00Z",
        "derived_profile": "B",
        "quiz_answers": "null",
        "optional_note": "",
        "shown_products": "123",
        "stroller_favorites": "null",
        "accessory_favorites": "123",
    }

    html = build_email_html(session)

    assert "XYZ789" in html


async def test_email_subject_strips_header_control_characters():
    from app.services.email import send_handoff_email

    session = {
        "session_id": "sess1",
        "session_code": "ABC\r\nInjected\x00\x1f\x7f\u0085: bad",
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
    subjects = []

    async def capture_send(html, subject):
        subjects.append(subject)

    async def mock_update(session_id, status, retry_count):
        pass

    with patch("app.services.email._send_smtp", new=capture_send):
        with patch("app.services.email._update_email_status", new=mock_update):
            await send_handoff_email(session)

    assert subjects == ["The Baby's Corner — Sessie ABC  Injected    : bad"]


async def noop_sleep(delay):
    pass
