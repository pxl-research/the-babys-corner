from app.services.session_code import generate_session_code

VALID_CHARS = set("ABCDEFGHJKMNPQRSTUVWXYZ23456789")
AMBIGUOUS = set("0OI1L")


def test_session_code_format_excludes_ambiguous_chars():
    for _ in range(100):
        code = generate_session_code()
        assert len(code) == 6
        assert code == code.upper()
        assert set(code).issubset(VALID_CHARS)
        assert not set(code) & AMBIGUOUS


def test_session_code_uniqueness_sample():
    codes = {generate_session_code() for _ in range(1000)}
    assert len(codes) == 1000
