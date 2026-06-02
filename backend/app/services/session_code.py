import secrets

_CHARSET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_session_code() -> str:
    # Cryptographically secure: codes are used by staff to look up sessions, so
    # predictability/enumeration matter.
    return "".join(secrets.choice(_CHARSET) for _ in range(6))
