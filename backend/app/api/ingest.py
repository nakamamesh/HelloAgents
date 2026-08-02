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


@router.post("/eval")
async def run_eval(body: EvalRequest) -> dict:
    return await eval_gate.evaluate_deliverable(
        success_metrics=body.success_metrics,
        task=body.task,
        deliverable=body.deliverable,
    )
