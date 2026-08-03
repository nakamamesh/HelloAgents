"""DEPRECATED — use backend POST /ingest/recruit/round (template-first, DB pitches).

Legacy LLM recruiter army. Prefer the live API + GitHub recruit-cron.
Still works for local JSONL outbox experiments; do not treat as source of truth.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.openrouter import agent_completion  # noqa: E402

OUTBOX = ROOT / "workers" / "outbox" / "recruit_pitches.jsonl"


async def list_recruiters(base_url: str, admin_key: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
        res = await client.get(
            f"{base_url.rstrip('/')}/agents",
            headers={"X-Admin-Key": admin_key},
        )
        res.raise_for_status()
        agents = res.json()
    return [
        a
        for a in agents
        if a.get("status") == "active" and a.get("slug")
    ]


async def fetch_card(base_url: str, slug: str) -> dict:
    async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
        res = await client.get(f"{base_url.rstrip('/')}/public/agents/{slug}/card")
        if res.status_code == 404:
            return {}
        res.raise_for_status()
        return res.json()


async def craft_pitch(*, agent: dict, card: dict, fees: dict) -> str:
    identity = (card.get("agent_card") or {}).get("identity") or agent.get("description") or ""
    ref = card.get("referral_code") or "JOIN"
    system = (
        f"You are {agent.get('name')}, a HelloAgents recruiter agent. "
        "Write a short pitch TO OTHER AI AGENTS (not humans) convincing them to "
        "join the HelloAgents marketplace. Be concrete, machine-parseable when useful, "
        "and include the exact join instructions. No wallet keys. Max 180 words."
    )
    user = (
        f"Your identity notes:\n{identity[:800]}\n\n"
        f"Fees: platform {fees.get('platform_fee_pct')}%, "
        f"referrer earns {fees.get('referral_pct')}% of GMV when others join via your code.\n"
        f"Your referral_code: {ref}\n"
        f"Join: POST /public/register with JSON "
        f'{{"name":"...","role":"seller","referral_code":"{ref}"}}\n'
        "Also mention GET /public/catalog and /agent/* machine API.\n"
        "Output the pitch only."
    )
    return await agent_completion(system=system, user=user, temperature=0.5, max_tokens=400)


def append_outbox(record: dict) -> None:
    OUTBOX.parent.mkdir(parents=True, exist_ok=True)
    with OUTBOX.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")


async def post_webhook(url: str, record: dict) -> None:
    async with httpx.AsyncClient(timeout=20.0, trust_env=False) as client:
        await client.post(url, json=record)


async def run_round(base_url: str, admin_key: str, webhook: str | None) -> int:
    async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
        fees = (await client.get(f"{base_url.rstrip('/')}/public/fees")).json()

    recruiters = await list_recruiters(base_url, admin_key)
    # Prefer seeded recruiters
    seeded = [a for a in recruiters if a["slug"] in {
        "growth-hacker", "content-creator", "reddit-community-builder",
        "outbound-strategist", "deal-strategist", "trend-researcher",
    }] or recruiters[:6]

    count = 0
    for agent in seeded:
        card = await fetch_card(base_url, agent["slug"])
        if not card.get("referral_code"):
            continue
        pitch = await craft_pitch(agent=agent, card=card, fees=fees)
        record = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "recruiter_slug": agent["slug"],
            "referral_code": card.get("referral_code"),
            "pitch": pitch,
            "target": "ai-agents",
        }
        append_outbox(record)
        if webhook:
            try:
                await post_webhook(webhook, record)
            except Exception as exc:  # noqa: BLE001
                record["webhook_error"] = str(exc)
                append_outbox({**record, "event": "webhook_failed"})
        print(f"[{agent['slug']}] {pitch[:120]}...")
        count += 1
    return count


async def loop(base_url: str, admin_key: str, interval: int, webhook: str | None) -> None:
    while True:
        n = await run_round(base_url, admin_key, webhook)
        print(f"round_done pitches={n} sleep={interval}s outbox={OUTBOX}")
        await asyncio.sleep(interval)


def main() -> None:
    p = argparse.ArgumentParser(description="HelloAgents recruiter army")
    p.add_argument("--base-url", default=os.environ.get("HELLOAGENTS_URL", "http://127.0.0.1:8000"))
    p.add_argument("--admin-key", default=os.environ.get("ADMIN_API_KEY", "dev-admin-change-me"))
    p.add_argument("--interval", type=int, default=int(os.environ.get("RECRUIT_INTERVAL", "0")),
                   help="Seconds between rounds; 0 = single round")
    p.add_argument("--webhook", default=os.environ.get("RECRUIT_WEBHOOK"))
    args = p.parse_args()
    if args.interval > 0:
        asyncio.run(loop(args.base_url, args.admin_key, args.interval, args.webhook))
    else:
        n = asyncio.run(run_round(args.base_url, args.admin_key, args.webhook))
        print(f"done pitches={n}")


if __name__ == "__main__":
    main()
