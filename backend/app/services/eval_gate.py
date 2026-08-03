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
        "Reply with ONLY one JSON object, no markdown, no prose. "
        'Schema: {"score":0.0-1.0,"pass":true|false,"rationale":"short"} '
        "pass=true when score>=0.7."
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
        max_tokens=200,
    )
    reply = reply or ""
    parsed = _parse_eval_json(reply)
    if parsed is None:
        repair = await openrouter.agent_completion(
            system=(
                "Convert the evaluation notes into ONLY JSON "
                '{"score":0.0-1.0,"pass":true|false,"rationale":"short"}. No other text.'
            ),
            user=reply[:1500],
            temperature=0.0,
            max_tokens=120,
        )
        parsed = _parse_eval_json(repair or "")
        if parsed is None:
            return {"score": 0.0, "pass": False, "rationale": "unparseable", "raw": reply}
        reply = repair or reply
    score = float(parsed.get("score", 0))
    passed = bool(parsed.get("pass", score >= 0.7)) or score >= 0.7
    return {
        "score": score,
        "pass": passed,
        "rationale": str(parsed.get("rationale", "")),
        "raw": reply,
    }


def _parse_eval_json(text: str) -> dict[str, Any] | None:
    match = re.search(r"\{[^{}]*\}", text, flags=re.DOTALL)
    if not match:
        match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data
