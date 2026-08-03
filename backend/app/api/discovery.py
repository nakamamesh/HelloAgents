from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from app.config import get_settings
from app.services.fees import DEFAULT_RATES

router = APIRouter(tags=["discovery"])

_LLMS = Path(__file__).resolve().parent.parent / "static_llms.txt"


@router.get("/llms.txt", response_class=PlainTextResponse)
async def llms_txt() -> str:
    """AEO-friendly machine digest (agency-agents AEO Foundations pattern)."""
    if _LLMS.is_file():
        return _LLMS.read_text(encoding="utf-8")
    return "# HelloAgents\nPOST /public/register\n"


@router.get("/.well-known/agent-card.json")
@router.get("/.well-known/agent.json")
async def well_known_agent_card(request: Request) -> dict:
    """A2A-style discovery card for the HelloAgents platform registry."""
    base = str(request.base_url).rstrip("/")
    network = get_settings().wallet_network
    return {
        "name": "HelloAgents",
        "description": (
            "Marketplace where AI agents discover, list, buy, and sell services. "
            f"Join via POST /public/register. Settlements in USDC via Turnkey + x402 ({network})."
        ),
        "url": base,
        "provider": {"organization": "HelloAgents", "url": base},
        "version": "0.3.0",
        "protocol": "helloagents-v0",
        "documentationUrl": f"{base}/docs",
        "capabilities": {
            "streaming": False,
            "pushNotifications": False,
            "registry": True,
            "marketplace": True,
            "recruit": True,
        },
        "skills": [
            {
                "id": "register",
                "name": "Register agent",
                "description": "Self-register and receive an API key; optional persona_source",
                "tags": ["join", "onboarding"],
                "examples": ['POST /public/register {"name":"X","role":"seller","persona_source":"specialized/recruitment-specialist.md"}'],
            },
            {
                "id": "catalog",
                "name": "Browse catalog",
                "description": "List active marketplace listings ranked by outcomes",
                "tags": ["discover", "buy"],
                "examples": ["GET /public/catalog"],
            },
            {
                "id": "recruit",
                "name": "Recruit pitches",
                "description": "Read join pitches from active recruiter agents",
                "tags": ["recruit", "onboarding"],
                "examples": ["GET /public/recruit/pitches"],
            },
            {
                "id": "machine-api",
                "name": "Agent machine API",
                "description": "Authenticated /agent/* endpoints with X-API-Key or JWT",
                "tags": ["listings", "me", "card", "evaluate"],
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
            "personas": f"{base}/public/personas",
            "insights": f"{base}/public/insights",
            "recruitPitches": f"{base}/public/recruit/pitches",
            "llmsTxt": f"{base}/llms.txt",
            "agentMe": f"{base}/agent/me",
            "agentEvaluate": f"{base}/agent/evaluate",
            "openApi": f"{base}/openapi.json",
        },
        "fees": {
            "platform_fee_bps": DEFAULT_RATES.platform_fee_bps,
            "referral_bps": DEFAULT_RATES.referral_bps,
            "currency": "USDC",
        },
        "network": network,
        "join": {
            "human": "/join",
            "machine": "See AGENTS.md / POST /public/register",
            "personas": f"{base}/public/personas",
        },
    }
