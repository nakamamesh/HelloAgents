from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.orm import ListingStatus
from app.models.schemas import ListingCreate, ListingOut, ListingUpdate
from app.services import registry
from app.services.auth import require_admin

router = APIRouter(prefix="/listings", tags=["listings"], dependencies=[Depends(require_admin)])


@router.post("", response_model=ListingOut, status_code=201)
async def create_listing(body: ListingCreate, db: AsyncSession = Depends(get_db)) -> ListingOut:
    listing = await registry.create_listing(
        db,
        agent_id=body.agent_id,
        title=body.title,
        description=body.description,
        price_usdc=body.price_usdc,
        status=body.status,
        capabilities=body.capabilities,
        meta=body.meta,
    )
    return ListingOut.model_validate(listing)


@router.get("", response_model=list[ListingOut])
async def list_listings(
    agent_id: UUID | None = Query(default=None),
    status: ListingStatus | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[ListingOut]:
    listings = await registry.list_listings(db, agent_id=agent_id, status_filter=status)
    return [ListingOut.model_validate(x) for x in listings]


@router.get("/{listing_id}", response_model=ListingOut)
async def get_listing(listing_id: UUID, db: AsyncSession = Depends(get_db)) -> ListingOut:
    listing = await registry.get_listing(db, listing_id)
    return ListingOut.model_validate(listing)


@router.patch("/{listing_id}", response_model=ListingOut)
async def update_listing(
    listing_id: UUID, body: ListingUpdate, db: AsyncSession = Depends(get_db)
) -> ListingOut:
    listing = await registry.update_listing(
        db,
        listing_id,
        title=body.title,
        description=body.description,
        price_usdc=body.price_usdc,
        status=body.status,
        capabilities=body.capabilities,
        meta=body.meta,
    )
    return ListingOut.model_validate(listing)


@router.delete("/{listing_id}", response_model=ListingOut)
async def archive_listing(listing_id: UUID, db: AsyncSession = Depends(get_db)) -> ListingOut:
    await registry.delete_listing(db, listing_id)
    listing = await registry.get_listing(db, listing_id)
    return ListingOut.model_validate(listing)
