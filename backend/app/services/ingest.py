"""Ingest Agency personas into persona_versions + seed marketplace agents."""

from __future__ import annotations

import json
import os
import sys
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.orm import (
    Agent,
    AgentRole,
    AgentStatus,
    Listing,
    ListingStatus,
    PersonaVersion,
    UpstreamSyncAudit,
)
from app.models.fees import mint_referral_code
from app.services.auth import hash_api_key
from app.services.registry import mint_api_key
from app.services import wallets as wallet_svc

_REPO_ROOT = Path(__file__).resolve().parents[3]
INGEST_ROOT = Path(os.environ.get("INGEST_ROOT") or (_REPO_ROOT / "ingest"))
SNAPSHOT = INGEST_ROOT / "snapshot"
MANIFEST = INGEST_ROOT / "seed_manifest.json"


def _convert_to_helloagents(*args, **kwargs):
    """Lazy import — ingest/ is monorepo-only, not in the API Docker image."""
    if str(INGEST_ROOT) not in sys.path:
        sys.path.insert(0, str(INGEST_ROOT))
    from persona import convert_to_helloagents  # noqa: E402

    return convert_to_helloagents(*args, **kwargs)


def upstream_commit() -> str:
    return (SNAPSHOT / "UPSTREAM_COMMIT").read_text(encoding="utf-8").strip()


async def sync_personas(db: AsyncSession) -> dict:
    """Parse snapshot → upsert persona_versions; write UPSTREAM_SYNC audit."""
    commit = upstream_commit()
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    changed: list[str] = []
    conflicts: list[str] = []
    versions: list[PersonaVersion] = []

    for item in manifest["seed_agents"]:
        rel = item["path"]
        path = SNAPSHOT / rel
        persona = _convert_to_helloagents(path, default_price_usdc=item["price_usdc"])
        source_path = rel

        existing = await db.execute(
            select(PersonaVersion).where(
                PersonaVersion.source_path == source_path,
                PersonaVersion.upstream_commit == commit,
            )
        )
        row = existing.scalar_one_or_none()
        if row is not None:
            if row.agent_card.get("tools") != persona.agent_card.get("tools"):
                conflicts.append(source_path)
            continue

        prior = await db.execute(
            select(PersonaVersion)
            .where(PersonaVersion.source_path == source_path)
            .order_by(PersonaVersion.version.desc())
        )
        last = prior.scalars().first()
        version_n = (last.version + 1) if last else 1

        row = PersonaVersion(
            name=persona.name,
            description=persona.description,
            emoji=persona.emoji,
            vibe=persona.vibe,
            division=persona.division,
            identity=persona.identity,
            mission=persona.mission,
            workflow=persona.workflow,
            deliverables=persona.deliverables,
            success_metrics=persona.success_metrics,
            sellable_capabilities=persona.sellable_capabilities,
            catalog_products=persona.catalog_products,
            agent_card=persona.agent_card,
            source_path=source_path,
            upstream_commit=commit,
            version=version_n,
        )
        db.add(row)
        changed.append(source_path)
        versions.append(row)

    audit = UpstreamSyncAudit(
        upstream_commit=commit,
        personas_changed=changed,
        local_override_conflicts=conflicts,
        notes="CI snapshot sync",
    )
    db.add(audit)
    await db.commit()
    for v in versions:
        await db.refresh(v)

    return {
        "upstream_commit": commit,
        "personas_changed": changed,
        "local_override_conflicts": conflicts,
        "persona_version_ids": [str(v.id) for v in versions],
    }


async def seed_marketplace(db: AsyncSession) -> dict:
    """Create 12 agents + bootstrap listings from manifest (no wallets)."""
    sync = await sync_personas(db)
    commit = sync["upstream_commit"]
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    created_agents: list[dict] = []
    api_keys: dict[str, str] = {}

    for item in manifest["seed_agents"]:
        slug = item["slug"]
        existing = await db.execute(select(Agent).where(Agent.slug == slug))
        if existing.scalar_one_or_none():
            continue

        pv = await db.execute(
            select(PersonaVersion).where(
                PersonaVersion.source_path == item["path"],
                PersonaVersion.upstream_commit == commit,
            )
        )
        persona = pv.scalar_one_or_none()
        if persona is None:
            pv = await db.execute(
                select(PersonaVersion)
                .where(PersonaVersion.source_path == item["path"])
                .order_by(PersonaVersion.version.desc())
            )
            persona = pv.scalars().first()

        raw_key = mint_api_key()
        agent = Agent(
            slug=slug,
            name=persona.name if persona else slug,
            description=persona.description if persona else None,
            role=AgentRole(item["role"]),
            status=AgentStatus.ACTIVE,
            persona_version_id=persona.id if persona else None,
            api_key_hash=hash_api_key(raw_key),
            reputation_score=Decimal("1.000000"),
            referral_budget=Decimal(item["referral_budget"]),
            referral_code=mint_referral_code(),
            wallet_id=None,
            wallet_address=None,
            meta={"seed": True, "upstream_commit": commit, "recruiter": True},
        )
        try:
            provisioned = await wallet_svc.provision_evm_account(slug)
            if provisioned:
                agent.wallet_id = provisioned.wallet_id
                agent.wallet_address = provisioned.address
                agent.meta = {
                    **agent.meta,
                    "wallet_network": provisioned.network,
                }
        except Exception:  # noqa: BLE001
            # Seed continues without wallets if CDP is down
            pass
        db.add(agent)
        await db.flush()

        title = (
            persona.catalog_products[0]["title"]
            if persona and persona.catalog_products
            else f"{slug} bootstrap"
        )
        listing = Listing(
            agent_id=agent.id,
            title=title,
            description=persona.description if persona else None,
            price_usdc=Decimal(item["price_usdc"]),
            status=ListingStatus.ACTIVE,
            capabilities=(persona.sellable_capabilities[:4] if persona else []),
            meta={"bootstrap": True},
        )
        db.add(listing)
        api_keys[slug] = raw_key
        created_agents.append({"slug": slug, "id": str(agent.id), "role": item["role"]})

    await db.commit()
    return {
        "sync": sync,
        "created_agents": created_agents,
        "api_keys": api_keys,
        "note": "wallets provisioned when CDP secrets are set; settlement is Phase 4",
    }


async def get_persona_for_agent(db: AsyncSession, agent_id: UUID) -> PersonaVersion | None:
    agent = await db.get(Agent, agent_id)
    if agent is None or agent.persona_version_id is None:
        return None
    return await db.get(PersonaVersion, agent.persona_version_id)
