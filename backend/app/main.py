from contextlib import asynccontextmanager
import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import api_router
from app.config import get_settings
from app.services.rate_limit import RateLimitMiddleware


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from app.services.recruit_cron import start_recruit_cron

    cron_task = start_recruit_cron()
    try:
        yield
    finally:
        if cron_task is not None:
            cron_task.cancel()
            try:
                await cron_task
            except asyncio.CancelledError:
                pass


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version="0.3.0", lifespan=lifespan)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list(),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    return app


app = create_app()
