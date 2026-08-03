"""Best-effort webhook / event bus. Uses Redis when available; else in-memory ring."""

from __future__ import annotations

import json
import logging
from collections import deque
from datetime import datetime, timezone
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

_RING: deque[dict[str, Any]] = deque(maxlen=200)


async def emit(event: str, payload: dict[str, Any]) -> None:
    body = {
        "event": event,
        "at": datetime.now(timezone.utc).isoformat(),
        "payload": payload,
    }
    _RING.append(body)
    settings = get_settings()
    try:
        import redis.asyncio as redis

        client = redis.from_url(settings.redis_url, decode_responses=True)
        try:
            await client.lpush("ha:events", json.dumps(body))
            await client.ltrim("ha:events", 0, 499)
            # Pub/sub channel for agents that SUBSCRIBE
            await client.publish("ha:webhooks", json.dumps(body))
        finally:
            await client.aclose()
    except Exception:  # noqa: BLE001
        logger.debug("redis webhook emit failed; kept in memory ring", exc_info=True)


def recent(limit: int = 50) -> list[dict[str, Any]]:
    items = list(_RING)
    items.reverse()
    return items[:limit]
