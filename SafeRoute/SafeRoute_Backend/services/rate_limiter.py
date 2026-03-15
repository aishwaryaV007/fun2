"""
services/rate_limiter.py
========================
Shared in-memory rate limiting for the SafeRoute backend.

The limiter is intentionally lightweight and process-local. It is sufficient for
single-instance development and small deployments, while keeping the API surface
stable. Production deployments should move these counters to Redis or another
shared store if the backend is scaled horizontally.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request


class InMemoryRateLimiter:
    """Sliding-window request limiter keyed by scope and client identity."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def hit(self, scope: str, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time.monotonic()
        bucket_key = f"{scope}:{key}"

        with self._lock:
            bucket = self._events[bucket_key]
            cutoff = now - window_seconds
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= limit:
                retry_after = max(1, int(window_seconds - (now - bucket[0])))
                return True, retry_after

            bucket.append(now)
            return False, 0


rate_limiter = InMemoryRateLimiter()


def build_rate_limit_key(request: Request, subject: str | None = None) -> str:
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    client_host = forwarded_for or (request.client.host if request.client else "unknown")
    if subject:
        return f"{client_host}:{subject}"
    return client_host


def enforce_rate_limit(
    request: Request,
    *,
    scope: str,
    limit: int,
    window_seconds: int,
    subject: str | None = None,
) -> None:
    blocked, retry_after = rate_limiter.hit(
        scope=scope,
        key=build_rate_limit_key(request, subject),
        limit=limit,
        window_seconds=window_seconds,
    )
    if blocked:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded for {scope}. Retry after {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )
