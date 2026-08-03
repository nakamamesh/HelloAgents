from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.services import eval_gate, ingest
from app.services.auth import require_admin
from pydantic import BaseModel, Field

router = APIRouter(prefix="/ingest", tags=["ingest"], dependencies=[Depends(require_admin)])


class EvalRequest(BaseModel):
    success_metrics: str | None = None
    task: str
    deliverable: str = Field(..., min_length=1)


@router.post("/sync")
async def sync_personas(db: AsyncSession = Depends(get_db)) -> dict:
    return await ingest.sync_personas(db)


@router.post("/seed")
async def seed_marketplace(db: AsyncSession = Depends(get_db)) -> dict:
    return await ingest.seed_marketplace(db)


@router.post("/wallets/backfill")
async def backfill_wallets(db: AsyncSession = Depends(get_db)) -> dict:
    """Provision Turnkey wallets for agents missing wallet_address."""
    from app.models.orm import Agent
    from app.services import wallets as wallet_svc

    if not wallet_svc.wallet_configured():
        return {"ok": False, "error": "Turnkey secrets not configured"}

    result = await db.execute(select(Agent).where(Agent.wallet_address.is_(None)))
    agents = list(result.scalars().all())
    updated: list[str] = []
    errors: list[dict] = []
    for agent in agents:
        try:
            provisioned = await wallet_svc.provision_evm_account(agent.slug)
            if provisioned is None:
                continue
            agent.wallet_id = provisioned.wallet_id
            agent.wallet_address = provisioned.address
            agent.meta = {**(agent.meta or {}), "wallet_network": provisioned.network}
            updated.append(agent.slug)
        except Exception as exc:  # noqa: BLE001
            errors.append({"slug": agent.slug, "error": str(exc)})
    await db.commit()

    treasury = None
    policies = None
    try:
        t = await wallet_svc.ensure_treasury_wallet()
        if t:
            treasury = {"wallet_id": t.wallet_id, "address": t.address, "network": t.network}
            policies = await wallet_svc.ensure_spend_policies(treasury_address=t.address)
    except Exception as exc:  # noqa: BLE001
        errors.append({"slug": "platform-treasury", "error": str(exc)})

    return {
        "updated": updated,
        "skipped_already_set": 0,
        "errors": errors,
        "treasury": treasury,
        "policies": policies,
    }


@router.post("/wallets/policies")
async def apply_wallet_policies() -> dict:
    """Apply Turnkey spend-limit + USDC/treasury allowlist policies."""
    from app.services import wallets as wallet_svc

    return await wallet_svc.ensure_spend_policies()


@router.get("/wallets/policies/audit")
async def audit_wallet_policies() -> dict:
    """Flag unrestricted SIGN_* ALLOW policies that can bypass HelloAgents guards."""
    from app.services import wallets as wallet_svc

    return await wallet_svc.audit_spend_policies()


@router.get("/wallets/treasury")
async def treasury_wallet_status() -> dict:
    """Treasury ETH/USDC balances — alert when gas is low."""
    from app.services import wallets as wallet_svc

    return await wallet_svc.treasury_status()


@router.post("/settlements/{txn_id}/retry-payouts")
async def retry_settlement_payouts(
    txn_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Retry treasury→seller/referrer after settle OK but disperse failed."""
    from app.services import settlement

    try:
        return await settlement.retry_payouts(db, txn_id=txn_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc


@router.post("/learning/backfill")
async def learning_backfill(db: AsyncSession = Depends(get_db)) -> dict:
    """Recompute listing/seller outcome counters from completed transactions."""
    from app.services import learning as learn_svc

    return await learn_svc.backfill_outcomes(db)


@router.post("/personas/refresh-caps")
async def refresh_persona_caps(db: AsyncSession = Depends(get_db)) -> dict:
    """Re-sync persona parse + push caps onto bootstrap listings."""
    sync = await ingest.sync_personas(db)
    caps = await ingest.refresh_listing_capabilities(db)
    return {"sync": sync, "listings": caps}


@router.post("/fulfillment/expire")
async def expire_deliveries(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    from app.services import fulfillment as ful

    return await ful.expire_overdue(db, limit=limit)


@router.post("/settlements/{txn_id}/refund")
async def admin_refund(
    txn_id: UUID,
    db: AsyncSession = Depends(get_db),
    note: str | None = Query(default=None, max_length=500),
) -> dict:
    """Mark transaction REFUNDED after treasury clawback (human ops)."""
    from app.services import fulfillment as ful

    try:
        return await ful.admin_mark_refunded(db, txn_id=txn_id, note=note)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/events")
async def list_events(limit: int = Query(default=50, ge=1, le=200)) -> dict:
    from app.services import webhooks as wh

    return {"events": wh.recent(limit)}


@router.post("/recruit/round")
async def recruit_round(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=12, ge=1, le=50),
    squad: str | None = Query(default=None, max_length=64),
) -> dict:
    """Craft recruiter pitches. Optional squad=growth|reddit|outbound|orchestrators."""
    from app.services import recruit as recruit_svc

    try:
        return await recruit_svc.run_recruit_round(db, limit=limit, squad=squad)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/recruit/outbound-status")
async def recruit_outbound_status() -> dict:
    from app.services import recruit as recruit_svc

    return recruit_svc.outbound_status()



@router.get("/recruit/pitches")
async def list_recruit_pitches(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    from app.models.recruit import RecruitPitch

    result = await db.execute(
        select(RecruitPitch).order_by(RecruitPitch.created_at.desc()).limit(limit)
    )
    rows = list(result.scalars().all())
    return {
        "pitches": [
            {
                "id": str(r.id),
                "recruiter_slug": r.recruiter_slug,
                "referral_code": r.referral_code,
                "pitch": r.pitch,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.post("/eval")
async def run_eval(body: EvalRequest) -> dict:
    return await eval_gate.evaluate_deliverable(
        success_metrics=body.success_metrics,
        task=body.task,
        deliverable=body.deliverable,
    )
