from fastapi import APIRouter, Depends
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
    """Provision CDP wallets for agents missing wallet_address."""
    from sqlalchemy import select

    from app.models.orm import Agent
    from app.services import wallets as wallet_svc

    if not wallet_svc.cdp_configured():
        return {"ok": False, "error": "CDP secrets not configured"}

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
    try:
        t = await wallet_svc.ensure_treasury_wallet()
        if t:
            treasury = {"wallet_id": t.wallet_id, "address": t.address, "network": t.network}
    except Exception as exc:  # noqa: BLE001
        errors.append({"slug": "platform-treasury", "error": str(exc)})

    return {
        "updated": updated,
        "skipped_already_set": 0,
        "errors": errors,
        "treasury": treasury,
    }


@router.post("/eval")
async def run_eval(body: EvalRequest) -> dict:
    return await eval_gate.evaluate_deliverable(
        success_metrics=body.success_metrics,
        task=body.task,
        deliverable=body.deliverable,
    )
