"""Simple per-IP sliding window rate limit (Redis preferred, memory fallback)."""

from __future__ import annotations

import logging
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import get_settings

logger = logging.getLogger(__name__)

_WINDOWS: dict[str, deque[float]] = defaultdict(deque)

_LIMITED_PREFIXES = (
    "/public/register",
    "/agent/buy",
    "/agent/evaluate",
    "/agent/deliver",
    "/agent/review",
)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        settings = get_settings()
        limit = settings.rate_limit_per_minute
        if limit <= 0 or request.method == "OPTIONS":
            return await call_next(request)
        path = request.url.path
        if not any(path.startswith(p) for p in _LIMITED_PREFIXES):
            return await call_next(request)
        if request.method not in ("POST", "PUT", "PATCH"):
            return await call_next(request)

        key = f"{_client_ip(request)}:{path.split('/')[1]}"
        now = time.time()
        window = 60.0

        # Try Redis
        try:
            import redis.asyncio as redis

            client = redis.from_url(settings.redis_url, decode_responses=True)
            try:
                rkey = f"ha:rl:{key}"
                count = await client.incr(rkey)
                if count == 1:
                    await client.expire(rkey, int(window))
                if count > limit:
                    return JSONResponse(
                        status_code=429,
                        content={"detail": "rate limit exceeded", "limit_per_minute": limit},
                    )
            finally:
                await client.aclose()
        except Exception:  # noqa: BLE001
            # Memory fallback
            q = _WINDOWS[key]
            while q and now - q[0] > window:
                q.popleft()
            if len(q) >= limit:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "rate limit exceeded", "limit_per_minute": limit},
                )
            q.append(now)

        return await call_next(request)
