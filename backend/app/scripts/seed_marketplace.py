"""CLI: seed marketplace from Agency snapshot."""

from __future__ import annotations

import asyncio
import json

from app.db.session import SessionLocal
from app.services.ingest import seed_marketplace


async def main() -> None:
    async with SessionLocal() as db:
        result = await seed_marketplace(db)
    # print without dumping full keys in CI logs optionally — operator needs them once
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
