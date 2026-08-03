"""Machine API for agents — /agent/* (API key or JWT)."""

from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.session import get_db
from app.models.orm import Agent
from app.models.schemas import (
    AgentOut,
    ListingOut,
    MachineListingCreate,
    TokenResponse,
)
from app.services import registry
from app.services.auth import create_agent_jwt, get_current_agent

router = APIRouter(prefix="/agent", tags=["machine"])


@router.post("/token", response_model=TokenResponse)
async def exchange_token(agent: Agent = Depends(get_current_agent)) -> TokenResponse:
    """Exchange API key (X-API-Key or Bearer ha_…) for a short-lived JWT."""
    settings = get_settings()
    token = create_agent_jwt(agent.id)
    return TokenResponse(
        access_token=token,
        expires_minutes=settings.jwt_expires_minutes,
        agent_id=agent.id,
        slug=agent.slug,
    )


@router.get("/me", response_model=AgentOut)
async def me(agent: Agent = Depends(get_current_agent)) -> AgentOut:
    return AgentOut.model_validate(agent)


@router.get("/wallet")
async def my_wallet(agent: Agent = Depends(get_current_agent)) -> dict:
    """Turnkey wallet id/address + live balances (Base Sepolia until mainnet cutover)."""
    from app.services import wallets as wallet_svc

    if not agent.wallet_address:
        return {
            "wallet_id": agent.wallet_id,
            "wallet_address": None,
            "configured": wallet_svc.wallet_configured(),
            "balances": [],
            "hint": "No wallet yet — set Turnkey secrets and POST /ingest/wallets/backfill",
        }
    balances = await wallet_svc.list_balances(agent.wallet_address)
    return {
        "wallet_id": agent.wallet_id,
        "wallet_address": agent.wallet_address,
        **balances,
    }


@router.get("/card")
async def my_card(
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Return persona agent_card used as the worker system-prompt source."""
    if agent.persona_version_id is None:
        return {"agent_id": str(agent.id), "slug": agent.slug, "agent_card": {}}
    from app.models.orm import PersonaVersion

    persona = await db.get(PersonaVersion, agent.persona_version_id)
    return {
        "agent_id": str(agent.id),
        "slug": agent.slug,
        "persona_version_id": str(agent.persona_version_id),
        "agent_card": persona.agent_card if persona else {},
        "sellable_capabilities": persona.sellable_capabilities if persona else [],
    }


@router.get("/listings", response_model=list[ListingOut])
async def my_listings(
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
) -> list[ListingOut]:
    listings = await registry.list_listings(db, agent_id=agent.id)
    return [ListingOut.model_validate(x) for x in listings]


@router.post("/listings", response_model=ListingOut, status_code=201)
async def create_my_listing(
    body: MachineListingCreate,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
) -> ListingOut:
    listing = await registry.create_listing(
        db,
        agent_id=agent.id,
        title=body.title,
        description=body.description,
        price_usdc=body.price_usdc,
        capabilities=body.capabilities,
        meta=body.meta,
    )
    return ListingOut.model_validate(listing)


class BuyRequest(BaseModel):
    listing_id: UUID
    idempotency_key: str = Field(..., min_length=8, max_length=128)


class EvaluateRequest(BaseModel):
    task: str = Field(..., min_length=1, max_length=4000)
    deliverable: str = Field(..., min_length=1, max_length=50000)
    transaction_id: UUID | None = None


class DeliverRequest(BaseModel):
    transaction_id: UUID
    artifact_uri: str = Field(..., min_length=1, max_length=4000)
    artifact_payload: str | None = Field(default=None, max_length=100_000)


class ReviewRequest(BaseModel):
    transaction_id: UUID
    score: Decimal = Field(..., max_digits=5, decimal_places=4)
    notes: str | None = Field(default=None, max_length=4000)
    accept: bool = True

    @field_validator("score", mode="before")
    @classmethod
    def no_float(cls, v: object) -> object:
        if isinstance(v, float):
            raise ValueError("use string Decimal, not float")
        return v


class RefundRequest(BaseModel):
    transaction_id: UUID
    reason: str = Field(..., min_length=3, max_length=1000)


@router.get("/transactions")
async def my_transactions(
    role: str | None = Query(default=None, pattern="^(buyer|seller)$"),
    limit: int = Query(default=50, ge=1, le=200),
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
) -> dict:
    from app.services import fulfillment as ful

    rows = await ful.list_agent_transactions(db, agent=agent, limit=limit, role=role)
    return {"agent_id": str(agent.id), "count": len(rows), "transactions": rows}


@router.post("/buy")
async def buy_listing(
    body: BuyRequest,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Create checkout (pending txn + fee split) and return x402 payment requirements."""
    from fastapi import HTTPException, status

    from app.services import settlement

    try:
        result = await settlement.create_checkout(
            db,
            buyer=agent,
            listing_id=body.listing_id,
            idempotency_key=body.idempotency_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    txn = result.transaction
    return {
        "transaction_id": str(txn.id),
        "status": txn.status.value if hasattr(txn.status, "value") else str(txn.status),
        "reused": result.reused,
        "payment": result.payment_requirements,
    }


@router.post("/buy/{txn_id}/pay")
async def pay_checkout(
    txn_id: UUID,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Sign USDC TransferWithAuthorization via Turnkey and settle through XPay facilitator."""
    from fastapi import HTTPException, status

    from app.services import settlement

    try:
        return await settlement.pay_and_settle(db, buyer=agent, txn_id=txn_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc


@router.post("/deliver")
async def deliver_order(
    body: DeliverRequest,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Seller submits artifact for a settled transaction."""
    from fastapi import HTTPException, status

    from app.services import fulfillment as ful

    try:
        return await ful.deliver(
            db,
            seller=agent,
            txn_id=body.transaction_id,
            artifact_uri=body.artifact_uri,
            artifact_payload=body.artifact_payload,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/review")
async def review_delivery(
    body: ReviewRequest,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Buyer scores a delivery; accept=true closes the loop, false opens dispute."""
    from fastapi import HTTPException, status

    from app.services import fulfillment as ful

    try:
        return await ful.review(
            db,
            buyer=agent,
            txn_id=body.transaction_id,
            score=body.score,
            notes=body.notes,
            accept=body.accept,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/refund")
async def refund_request(
    body: RefundRequest,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Request refund (ledger flag). On-chain return is admin/treasury."""
    from fastapi import HTTPException, status

    from app.services import fulfillment as ful

    try:
        return await ful.request_refund(
            db, agent=agent, txn_id=body.transaction_id, reason=body.reason
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/evaluate")
async def evaluate_deliverable(
    body: EvaluateRequest,
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Score a deliverable against persona success_metrics; on pass bump reputation + evolve meta."""
    from fastapi import HTTPException, status

    from app.models.orm import PersonaVersion, Transaction
    from app.services import eval_gate, reputation as rep_svc
    from app.services.openrouter import OpenRouterError

    metrics = None
    deliverable = body.deliverable
    if body.transaction_id:
        txn = await db.get(Transaction, body.transaction_id)
        if txn and txn.artifact_uri and (not deliverable or deliverable == "."):
            deliverable = txn.artifact_uri
    if agent.persona_version_id:
        persona = await db.get(PersonaVersion, agent.persona_version_id)
        if persona:
            metrics = persona.success_metrics
    try:
        result = await eval_gate.evaluate_deliverable(
            success_metrics=metrics,
            deliverable=deliverable,
            task=body.task,
        )
    except OpenRouterError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    improve = None
    if result.get("pass"):
        improve = await rep_svc.apply_eval_pass(
            db, agent=agent, score=float(result.get("score") or 0), task=body.task
        )
        await db.commit()
        await db.refresh(agent)
    return {
        "agent_id": str(agent.id),
        "slug": agent.slug,
        "transaction_id": str(body.transaction_id) if body.transaction_id else None,
        "eval": result,
        "self_improve": improve,
        "reputation_score": str(agent.reputation_score),
    }


@router.get("/badges")
async def my_badges(
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
) -> dict:
    from app.services import reputation as rep_svc

    return {
        "agent_id": str(agent.id),
        "slug": agent.slug,
        "reputation_score": str(agent.reputation_score),
        "badges": await rep_svc.list_badges(db, agent_id=agent.id),
    }


@router.post("/recruit")
async def publish_my_recruit_pitch(
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Publish a join pitch with this agent's referral_code (army self-recruit)."""
    from fastapi import HTTPException, status

    from app.services import recruit as recruit_svc

    try:
        pitch = await recruit_svc.publish_pitch(db, agent=agent, broadcast=True)
        await db.commit()
        return {"ok": True, "pitch": pitch}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/referrals")
async def my_referrals(
    agent: Agent = Depends(get_current_agent),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Downline agents + referral USDC earned."""
    from app.services import recruit as recruit_svc

    return await recruit_svc.agent_referrals(db, agent=agent)
