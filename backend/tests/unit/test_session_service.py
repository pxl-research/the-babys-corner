from app.services.session_service import parse_json_field


def test_parse_json_field_decodes_valid_json():
    assert parse_json_field('["a", "b"]', []) == ["a", "b"]
    assert parse_json_field('{"k": 1}', {}) == {"k": 1}


def test_parse_json_field_returns_default_for_blank():
    assert parse_json_field(None, []) == []
    assert parse_json_field("", {}) == {}


def test_parse_json_field_returns_default_for_malformed():
    assert parse_json_field("{not json", []) == []
    assert parse_json_field("['unterminated", None) is None
