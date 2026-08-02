"""Thin async HelloAgents workers.

Workers call OpenRouter `deepseek/deepseek-v4-flash` directly (BYOK via env).
No third-party agent orchestration runtime.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Allow importing backend openrouter when run from monorepo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.openrouter import agent_completion  # noqa: E402


async def run_worker(system: str, task: str) -> str:
    return await agent_completion(system=system, user=task)


if __name__ == "__main__":
    reply = asyncio.run(
        run_worker(
            "You are a HelloAgents worker smoke test.",
            "Say: worker-ok",
        )
    )
    print(reply)
