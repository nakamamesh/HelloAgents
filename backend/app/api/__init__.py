from fastapi import APIRouter

from app.api import agents, health, listings, machine

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(agents.router)
api_router.include_router(listings.router)
api_router.include_router(machine.router)
