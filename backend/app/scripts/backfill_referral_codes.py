"""Backfill referral_code for agents missing one."""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.fees import mint_referral_code
from app.models.orm import Agent


async def main() -> None:
    async with SessionLocal() as db:
        result = await db.execute(select(Agent).where(Agent.referral_code.is_(None)))
        agents = list(result.scalars().all())
        for agent in agents:
            code = mint_referral_code()
            while True:
                clash = await db.execute(select(Agent).where(Agent.referral_code == code))
                if clash.scalar_one_or_none() is None:
                    break
                code = mint_referral_code()
            agent.referral_code = code
            meta = dict(agent.meta or {})
            meta["recruiter"] = True
            agent.meta = meta
        await db.commit()
        print(f"backfilled={len(agents)}")


if __name__ == "__main__":
    asyncio.run(main())
