"""OpenRouter client — DeepSeek V4 Flash via BYOK server-side key."""

from __future__ import annotations

import asyncio
import os
from typing import Any

import httpx

from app.config import get_settings

DEFAULT_MODEL = "deepseek/deepseek-v4-flash"


class OpenRouterError(RuntimeError):
    """Raised when OpenRouter returns a non-success response."""


async def chat(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Low-level chat completions call. Returns full OpenRouter JSON body."""
    settings = get_settings()
    api_key = (settings.openrouter_api_key or os.environ.get("OPENROUTER_API_KEY", "")).strip()
    if not api_key or api_key.endswith("REPLACE_ME"):
        raise OpenRouterError("OPENROUTER_API_KEY is not set")

    payload: dict[str, Any] = {
        "model": model or settings.openrouter_model or DEFAULT_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if extra:
        payload.update(extra)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://helloagents.local",
        "X-Title": "HelloAgents",
    }

    url = f"{settings.openrouter_base_url.rstrip('/')}/chat/completions"
    async with httpx.AsyncClient(timeout=60.0, trust_env=False) as client:
        resp = await client.post(url, headers=headers, json=payload)

    if resp.status_code >= 400:
        raise OpenRouterError(f"OpenRouter {resp.status_code}: {resp.text}")

    return resp.json()


async def agent_completion(
    system: str,
    user: str,
    *,
    model: str | None = None,
    temperature: float = 0.4,
    max_tokens: int = 2048,
) -> str:
    """Agent-oriented helper: system + user → assistant text content."""
    data = await chat(
        [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise OpenRouterError(f"Unexpected response shape: {data!r}") from exc


async def _smoke() -> None:
    reply = await agent_completion(
        system="You are a concise HelloAgents smoke-test assistant.",
        user="Reply with exactly one short sentence confirming you are deepseek-v4-flash via OpenRouter.",
        temperature=0.2,
        max_tokens=64,
    )
    print(reply)


if __name__ == "__main__":
    asyncio.run(_smoke())
