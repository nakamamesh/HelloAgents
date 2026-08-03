"""Agency persona parsing + HelloAgents conversion.

Architectural mirror of agency-agents scripts/lib.sh + convert.sh:
frontmatter fields + body sections → structured persona → agent card.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


HELLOAGENTS_TOOLS = [
    {
        "name": "list",
        "description": "Browse marketplace listings matching a capability query",
        "parameters": {"query": "string", "role": "seller|publisher|buyer"},
    },
    {
        "name": "buy",
        "description": "Purchase a listing (USDC on Base via Turnkey + x402)",
        "parameters": {"listing_id": "uuid", "idempotency_key": "string"},
    },
    {
        "name": "deliver",
        "description": "Deliver work product / digital good for an order",
        "parameters": {"transaction_id": "uuid", "artifact_uri": "string"},
    },
    {
        "name": "evaluate",
        "description": "Score another agent's deliverable against success metrics",
        "parameters": {"transaction_id": "uuid", "notes": "string"},
    },
]


SECTION_ALIASES = {
    "identity": ("identity", "identity & role definition", "identity and role"),
    "mission": ("mission", "core mission", "purpose"),
    "workflow": ("workflow", "operating workflow", "process", "decision framework"),
    "deliverables": ("deliverables", "outputs", "core capabilities"),
    "success_metrics": ("success metrics", "success criteria", "metrics"),
}


@dataclass
class Persona:
    name: str
    description: str | None
    emoji: str | None
    vibe: str | None
    division: str
    identity: str | None
    mission: str | None
    workflow: str | None
    deliverables: str | None
    success_metrics: str | None
    source_path: str
    sellable_capabilities: list[str] = field(default_factory=list)
    catalog_products: list[dict[str, Any]] = field(default_factory=list)
    agent_card: dict[str, Any] = field(default_factory=dict)
    raw_frontmatter: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        raise ValueError("missing YAML frontmatter fence")
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError("unterminated frontmatter")
    fm_raw, body = parts[1], parts[2].lstrip("\n")
    meta: dict[str, str] = {}
    for line in fm_raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, val = line.split(":", 1)
        meta[key.strip()] = val.strip().strip('"').strip("'")
    return meta, body


def _split_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in body.splitlines():
        if line.startswith("## "):
            if current is not None:
                sections[current] = "\n".join(buf).strip()
            current = line[3:].strip().lower()
            buf = []
        else:
            buf.append(line)
    if current is not None:
        sections[current] = "\n".join(buf).strip()
    return sections


def _pick_section(sections: dict[str, str], aliases: tuple[str, ...]) -> str | None:
    for alias in aliases:
        for key, val in sections.items():
            if alias in key:
                return val
    return None


def _slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _capabilities_from_text(text: str | None) -> list[str]:
    if not text:
        return []
    caps: list[str] = []
    for line in text.splitlines():
        m = re.match(r"^[-*]\s+\*?\*?([^*\n:]+)", line.strip())
        if m:
            caps.append(m.group(1).strip()[:120])
        if len(caps) >= 8:
            break
    return caps


def convert_to_helloagents(
    path: Path,
    *,
    division: str | None = None,
    default_price_usdc: str = "5.000000",
) -> Persona:
    text = path.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)
    sections = _split_sections(body)
    div = division or path.parent.name

    name = meta.get("name") or path.stem
    description = meta.get("description")
    identity = _pick_section(sections, SECTION_ALIASES["identity"]) or description
    mission = _pick_section(sections, SECTION_ALIASES["mission"])
    workflow = _pick_section(sections, SECTION_ALIASES["workflow"])
    deliverables = _pick_section(sections, SECTION_ALIASES["deliverables"])
    success_metrics = _pick_section(sections, SECTION_ALIASES["success_metrics"])
    caps = _capabilities_from_text(deliverables) or _capabilities_from_text(identity)

    catalog = [
        {
            "sku": f"{_slugify(name)}-bootstrap",
            "title": f"{name} bootstrap service",
            "price_usdc": default_price_usdc,
            "capabilities": caps[:4],
        }
    ]

    agent_card = {
        "identity": identity,
        "mission": mission,
        "workflow": workflow,
        "success_metrics": success_metrics,
        "tools": HELLOAGENTS_TOOLS,
        "roles": ["seller", "publisher", "buyer"],
    }

    return Persona(
        name=name,
        description=description,
        emoji=meta.get("emoji"),
        vibe=meta.get("vibe"),
        division=div,
        identity=identity,
        mission=mission,
        workflow=workflow,
        deliverables=deliverables,
        success_metrics=success_metrics,
        source_path=str(path).replace("\\", "/"),
        sellable_capabilities=caps,
        catalog_products=catalog,
        agent_card=agent_card,
        raw_frontmatter=meta,
    )


def discover_personas(snapshot_root: Path) -> list[Path]:
    return sorted(snapshot_root.glob("*/*.md"))
