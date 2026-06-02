"""Signed role tokens for staff/admin auth, carried in an HttpOnly cookie.

The token is `role.expiry.signature` where the signature is an HMAC over
`role.expiry` keyed by the app secret. It is stateless (no server storage) and
tamper-evident; credentials never leave the browser after login.
"""

import base64
import hashlib
import hmac
import time

from app.config import settings

_SEP = "."
_ROLES = ("staff", "admin")
DEFAULT_TTL_SECONDS = 8 * 3600
COOKIE_NAME = "auth_token"


def _sign(payload: str) -> str:
    digest = hmac.new(settings.session_secret_key.encode(), payload.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def issue_token(role: str, ttl_seconds: int = DEFAULT_TTL_SECONDS) -> str:
    if role not in _ROLES:
        raise ValueError(f"Unknown role: {role}")
    payload = f"{role}{_SEP}{int(time.time()) + ttl_seconds}"
    return f"{payload}{_SEP}{_sign(payload)}"


def verify_token(token: str | None) -> str | None:
    """Return the role if the token is valid and unexpired, else None."""
    if not token:
        return None
    parts = token.split(_SEP)
    if len(parts) != 3:
        return None
    role, exp, sig = parts
    if not hmac.compare_digest(sig, _sign(f"{role}{_SEP}{exp}")):
        return None
    try:
        if int(exp) < int(time.time()):
            return None
    except ValueError:
        return None
    return role if role in _ROLES else None
