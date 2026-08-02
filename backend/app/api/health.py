from fastapi import APIRouter

from app.config import get_settings
from app.models.schemas import HealthResponse, OpenRouterSmokeResponse
from app.services import openrouter

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    s = get_settings()
    return HealthResponse(status="ok", app=s.app_name, env=s.app_env)


@router.get("/health/openrouter", response_model=OpenRouterSmokeResponse)
async def health_openrouter() -> OpenRouterSmokeResponse:
    s = get_settings()
    reply = await openrouter.agent_completion(
        system="You are a concise HelloAgents health-check assistant.",
        user="Reply with exactly: openrouter-ok",
        temperature=0.0,
        max_tokens=16,
    )
    return OpenRouterSmokeResponse(model=s.openrouter_model, reply=reply.strip())
