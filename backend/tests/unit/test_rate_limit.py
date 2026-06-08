import pytest
from fastapi import HTTPException

from app.services.rate_limit import check_rate_limit, clear_rate_limit_state


@pytest.fixture(autouse=True)
def reset_rate_limits():
    clear_rate_limit_state()
    yield
    clear_rate_limit_state()


def test_check_rate_limit_accepts_positional_limit_args():
    check_rate_limit("key", 2, 60, now_fn=lambda: 1.0)
    check_rate_limit("key", 2, 60, now_fn=lambda: 2.0)

    with pytest.raises(HTTPException) as exc:
        check_rate_limit("key", 2, 60, now_fn=lambda: 3.0)

    assert exc.value.status_code == 429


def test_check_rate_limit_expires_old_entries():
    check_rate_limit("key", 1, 60, now_fn=lambda: 1.0)

    check_rate_limit("key", 1, 60, now_fn=lambda: 62.0)
