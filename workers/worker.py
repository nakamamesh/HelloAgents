"""Thin HelloAgents worker — no orchestration runtime.

Loads agent identity from control plane (/agent/me), builds system prompt from
agent card fields when available, calls OpenRouter deepseek/deepseek-v4-flash.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.services.openrouter import agent_completion  # noqa: E402


def build_system_prompt(me: dict[str, Any], card: dict[str, Any] | None = None) -> str:
    card = card or {}
    parts = [
        f"You are {me.get('name')} ({me.get('slug')}), a HelloAgents marketplace agent.",
        f"Role: {me.get('role')}.",
    ]
    if me.get("description"):
        parts.append(me["description"])
    for key in ("identity", "mission", "workflow", "success_metrics"):
        if card.get(key):
            parts.append(f"## {key.replace('_', ' ').title()}\n{card[key]}")
    tools = card.get("tools") or []
    if tools:
        parts.append(
            "## Available HelloAgents tools (describe intent only; execution is orchestrated)\n"
            + json.dumps(tools)
        )
    parts.append("Be concise, practical, and complete. Never invent wallet keys or secrets.")
    return "\n\n".join(parts)


async def fetch_me(base_url: str, api_key: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.get(
            f"{base_url.rstrip('/')}/agent/me",
            headers={"X-API-Key": api_key},
        )
        res.raise_for_status()
        return res.json()


async def fetch_card(base_url: str, api_key: str) -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        res = await client.get(
            f"{base_url.rstrip('/')}/agent/card",
            headers={"X-API-Key": api_key},
        )
        res.raise_for_status()
        return res.json()


async def run_task(*, base_url: str, api_key: str, task: str, card_json: str | None) -> str:
    me = await fetch_me(base_url, api_key)
    if card_json:
        card = json.loads(card_json)
    else:
        card_payload = await fetch_card(base_url, api_key)
        card = card_payload.get("agent_card") or {}
    system = build_system_prompt(me, card)
    return await agent_completion(system=system, user=task, temperature=0.3, max_tokens=800)


def main() -> None:
    parser = argparse.ArgumentParser(description="HelloAgents thin worker")
    parser.add_argument("--base-url", default=os.environ.get("HELLOAGENTS_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--api-key", default=os.environ.get("AGENT_API_KEY", ""))
    parser.add_argument("--task", required=True)
    parser.add_argument("--card-json", default=None, help="Optional agent_card JSON override")
    args = parser.parse_args()
    if not args.api_key:
        raise SystemExit("Provide --api-key or AGENT_API_KEY")
    reply = asyncio.run(
        run_task(
            base_url=args.base_url,
            api_key=args.api_key.strip(),
            task=args.task,
            card_json=args.card_json,
        )
    )
    print(reply)


if __name__ == "__main__":
    main()
