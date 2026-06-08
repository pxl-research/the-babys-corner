import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import HTTPException, Request

_buckets: dict[str, deque[float]] = defaultdict(deque)


def clear_rate_limit_state() -> None:
    _buckets.clear()


def client_ip(request: Request) -> str:
    if request.client:
        return request.client.host
    return "unknown"


def check_rate_limit(
    key: str,
    limit: int,
    window_seconds: int,
    now_fn: Callable[[], float] = time.monotonic,
) -> None:
    now = now_fn()
    bucket = _buckets[key]
    cutoff = now - window_seconds
    while bucket and bucket[0] <= cutoff:
        bucket.popleft()
    if len(bucket) >= limit:
        raise HTTPException(429, detail="Too many requests.")
    bucket.append(now)
