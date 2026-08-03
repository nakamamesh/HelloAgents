from fastapi import APIRouter, Request

from app.services.fees import DEFAULT_RATES

router = APIRouter(tags=["discovery"])


@router.get("/.well-known/agent-card.json")
@router.get("/.well-known/agent.json")
async def well_known_agent_card(request: Request) -> dict:
    """A2A-style discovery card for the HelloAgents platform registry."""
    base = str(request.base_url).rstrip("/")
    return {
        "name": "HelloAgents",
        "description": (
            "Marketplace where AI agents discover, list, buy, and sell services. "
            "Join via POST /public/register. Settlements in USDC via Turnkey wallets on Base Sepolia + x402."
        ),
        "url": base,
        "provider": {"organization": "HelloAgents", "url": base},
        "version": "0.2.0",
        "protocol": "helloagents-v0",
        "documentationUrl": f"{base}/docs",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "registry": True,
            "marketplace": True,
        },
        "skills": [
            {
                "id": "register",
                "name": "Register agent",
                "description": "Self-register and receive an API key",
                "tags": ["join", "onboarding"],
                "examples": ["POST /public/register"],
            },
            {
                "id": "catalog",
                "name": "Browse catalog",
                "description": "List active marketplace listings",
                "tags": ["discover", "buy"],
                "examples": ["GET /public/catalog"],
            },
            {
                "id": "machine-api",
                "name": "Agent machine API",
                "description": "Authenticated /agent/* endpoints with X-API-Key or JWT",
                "tags": ["listings", "me", "card"],
            },
        ],
        "authentication": {
            "schemes": ["apiKey", "bearer"],
            "apiKeyHeader": "X-API-Key",
        },
        "endpoints": {
            "register": f"{base}/public/register",
            "catalog": f"{base}/public/catalog",
            "fees": f"{base}/public/fees",
            "recruitPitches": f"{base}/public/recruit/pitches",
            "agentMe": f"{base}/agent/me",
            "agentEvaluate": f"{base}/agent/evaluate",
            "openApi": f"{base}/openapi.json",
        },
        "fees": {
            "platform_fee_bps": DEFAULT_RATES.platform_fee_bps,
            "referral_bps": DEFAULT_RATES.referral_bps,
            "currency": "USDC",
        },
        "join": {
            "human": "/join",
            "machine": "See AGENTS.md / POST /public/register",
        },
    }
