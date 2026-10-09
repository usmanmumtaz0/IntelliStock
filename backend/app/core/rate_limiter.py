"""Redis-backed request limiting with a thread-safe single-process fallback."""
from __future__ import annotations

import hashlib
import logging
import threading
import time
from dataclasses import dataclass

import redis
from fastapi import HTTPException, Request, status

from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after: int


class RateLimiter:
    """Thread-safe fixed-window limiter used when Redis is unavailable."""

    def __init__(self):
        self.requests: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def check(self, identifier: str, limit: int, window_seconds: int) -> RateLimitResult:
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            timestamps = [value for value in self.requests.get(identifier, []) if value > cutoff]
            if len(timestamps) >= limit:
                retry = max(1, int(window_seconds - (now - timestamps[0])))
                self.requests[identifier] = timestamps
                return RateLimitResult(False, retry)
            timestamps.append(now)
            self.requests[identifier] = timestamps
        return RateLimitResult(True, window_seconds)

    def is_allowed(self, identifier: str, limit: int = 100, window_seconds: int = 60) -> bool:
        """Backward-compatible boolean interface."""
        return self.check(identifier, limit, window_seconds).allowed

    def reset(self) -> None:
        with self._lock:
            self.requests.clear()


class SharedRateLimiter:
    """Use Redis across workers and degrade to an explicitly local limiter."""

    def __init__(self, redis_url: str):
        self.redis_client = redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=settings.REDIS_SOCKET_TIMEOUT_SECONDS,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT_SECONDS,
        )
        self.fallback = RateLimiter()
        self._warned_about_fallback = False

    def check(self, identifier: str, limit: int, window_seconds: int) -> RateLimitResult:
        bucket = int(time.time() // window_seconds)
        key = f"rate-limit:{identifier}:{bucket}"
        try:
            pipeline = self.redis_client.pipeline()
            pipeline.incr(key)
            pipeline.expire(key, window_seconds + 1)
            count, _ = pipeline.execute()
            ttl = self.redis_client.ttl(key)
            return RateLimitResult(int(count) <= limit, max(1, int(ttl) if ttl and ttl > 0 else window_seconds))
        except redis.RedisError:
            if not self._warned_about_fallback:
                logger.warning(
                    "Redis rate limiting unavailable; using a per-process fallback that is not shared across workers"
                )
                self._warned_about_fallback = True
            return self.fallback.check(identifier, limit, window_seconds)


shared_rate_limiter = SharedRateLimiter(settings.REDIS_URL)
rate_limiter = RateLimiter()


def get_client_identifier(request: Request) -> str:
    """Return the direct peer IP unless trusted proxy handling is explicitly enabled."""
    ip = request.client.host if request.client else "unknown"
    if settings.TRUSTED_PROXY_HEADERS:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            ip = forwarded.split(",", 1)[0].strip() or ip
    return ip or "unknown"


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def enforce_login_rate_limit(request: Request, normalized_email: str) -> None:
    """Limit the effective login route by both peer IP and normalized account."""
    limit = settings.RATE_LIMIT_LOGIN_REQUESTS
    window = settings.RATE_LIMIT_LOGIN_WINDOW_SECONDS
    identifiers = (
        f"login:ip:{_digest(get_client_identifier(request))}",
        f"login:account:{_digest(normalized_email)}",
    )
    decisions = [shared_rate_limiter.check(identifier, limit, window) for identifier in identifiers]
    blocked = [decision for decision in decisions if not decision.allowed]
    if blocked:
        retry_after = max(decision.retry_after for decision in blocked)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )


async def check_rate_limit(request: Request) -> bool:
    """Apply a coarse non-login limit; login has its own account-aware limiter."""
    identifier = f"request:{_digest(get_client_identifier(request))}"
    decision = rate_limiter.check(
        identifier,
        settings.RATE_LIMIT_DEFAULT_REQUESTS,
        settings.RATE_LIMIT_DEFAULT_WINDOW_SECONDS,
    )
    if not decision.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again later.",
            headers={"Retry-After": str(decision.retry_after)},
        )
    return True


def get_rate_limit_status(identifier: str) -> dict:
    current = len(rate_limiter.requests.get(identifier, []))
    limit = settings.RATE_LIMIT_DEFAULT_REQUESTS
    return {
        "current": current,
        "limit": limit,
        "remaining": max(0, limit - current),
        "reset": time.time() + settings.RATE_LIMIT_DEFAULT_WINDOW_SECONDS,
    }
