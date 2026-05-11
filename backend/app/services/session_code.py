import random

_CHARSET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"


def generate_session_code() -> str:
    return "".join(random.choices(_CHARSET, k=6))
