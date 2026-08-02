from fastapi import APIRouter

from app.api import agents, health, ingest, listings, machine, public

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(agents.router)
api_router.include_router(listings.router)
api_router.include_router(machine.router)
api_router.include_router(ingest.router)
api_router.include_router(public.router)
