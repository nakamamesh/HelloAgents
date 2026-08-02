"""Eval gate — score a deliverable against persona success metrics via OpenRouter."""

from __future__ import annotations

import json
import re
from typing import Any

from app.services import openrouter


async def evaluate_deliverable(
    *,
    success_metrics: str | None,
    deliverable: str,
    task: str,
) -> dict[str, Any]:
    system = (
        "You are the HelloAgents evaluation gate. "
        "Score the deliverable against the success metrics. "
        "Respond with ONLY compact JSON: "
        '{"score":0.0-1.0,"pass":true|false,"rationale":"short"}'
    )
    user = (
        f"TASK:\n{task}\n\n"
        f"SUCCESS METRICS:\n{success_metrics or 'quality, clarity, completeness'}\n\n"
        f"DELIVERABLE:\n{deliverable}\n"
    )
    reply = await openrouter.agent_completion(
        system=system,
        user=user,
        temperature=0.0,
        max_tokens=256,
    )
    match = re.search(r"\{.*\}", reply, flags=re.DOTALL)
    if not match:
        return {"score": 0.0, "pass": False, "rationale": "unparseable", "raw": reply}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {"score": 0.0, "pass": False, "rationale": "invalid json", "raw": reply}
    score = float(data.get("score", 0))
    passed = bool(data.get("pass", score >= 0.7))
    return {
        "score": score,
        "pass": passed,
        "rationale": str(data.get("rationale", "")),
        "raw": reply,
    }
