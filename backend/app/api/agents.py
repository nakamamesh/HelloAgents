from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.orm import AgentRole, AgentStatus
from app.models.schemas import AgentCreate, AgentCreated, AgentOut, AgentUpdate
from app.services import registry
from app.services.auth import require_admin

router = APIRouter(prefix="/agents", tags=["agents"], dependencies=[Depends(require_admin)])


@router.post("", response_model=AgentCreated, status_code=201)
async def create_agent(body: AgentCreate, db: AsyncSession = Depends(get_db)) -> AgentCreated:
    agent, api_key = await registry.create_agent(
        db,
        slug=body.slug,
        name=body.name,
        role=body.role,
        description=body.description,
        status=body.status,
        referral_budget=body.referral_budget,
        reputation_score=body.reputation_score,
        meta=body.meta,
    )
    return AgentCreated(**AgentOut.model_validate(agent).model_dump(), api_key=api_key)


@router.get("", response_model=list[AgentOut])
async def list_agents(
    role: AgentRole | None = Query(default=None),
    status: AgentStatus | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[AgentOut]:
    agents = await registry.list_agents(db, role=role, status_filter=status)
    return [AgentOut.model_validate(a) for a in agents]


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(agent_id: UUID, db: AsyncSession = Depends(get_db)) -> AgentOut:
    agent = await registry.get_agent(db, agent_id)
    return AgentOut.model_validate(agent)


@router.patch("/{agent_id}", response_model=AgentOut)
async def update_agent(
    agent_id: UUID, body: AgentUpdate, db: AsyncSession = Depends(get_db)
) -> AgentOut:
    agent = await registry.update_agent(
        db,
        agent_id,
        name=body.name,
        description=body.description,
        status=body.status,
        meta=body.meta,
    )
    return AgentOut.model_validate(agent)


@router.post("/{agent_id}/rotate-key", response_model=AgentCreated)
async def rotate_key(agent_id: UUID, db: AsyncSession = Depends(get_db)) -> AgentCreated:
    agent, api_key = await registry.rotate_api_key(db, agent_id)
    return AgentCreated(**AgentOut.model_validate(agent).model_dump(), api_key=api_key)
