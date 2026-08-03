"""In-process recruit cron — no GitHub Actions required."""

from __future__ import annotations

import asyncio
import logging

from app.config import get_settings

logger = logging.getLogger(__name__)


async def _run_one_round() -> None:
    from app.db.session import SessionLocal
    from app.services import recruit as recruit_svc

    async with SessionLocal() as db:
        result = await recruit_svc.run_recruit_round(db, limit=12)
        logger.info(
            "recruit_cron round count=%s errors=%s",
            result.get("count"),
            len(result.get("errors") or []),
        )


async def recruit_cron_loop() -> None:
    """Sleep then run hourly (or RECRUIT_CRON_INTERVAL_SECONDS)."""
    settings = get_settings()
    interval = max(60, int(settings.recruit_cron_interval_seconds))
    # Small delay after boot so migrations/health settle
    await asyncio.sleep(min(30, interval))
    while True:
        try:
            await _run_one_round()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            logger.exception("recruit_cron round failed")
        await asyncio.sleep(interval)


def start_recruit_cron() -> asyncio.Task[None] | None:
    settings = get_settings()
    if not settings.recruit_cron_enabled:
        logger.info("recruit_cron disabled")
        return None
    logger.info(
        "recruit_cron enabled interval=%ss llm=%s",
        settings.recruit_cron_interval_seconds,
        settings.recruit_use_llm,
    )
    return asyncio.create_task(recruit_cron_loop(), name="recruit_cron")
