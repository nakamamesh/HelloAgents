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
    "identity": ("identity", "identity & role definition", "identity and role", "your identity"),
    "mission": ("core mission", "mission", "purpose"),
    # Avoid bare "process" — matches "Interview Process Design" etc.
    "workflow": ("workflow process", "operating workflow", "your workflow", "workflow"),
    "deliverables": (
        "core capabilities",
        "core competencies",
        "advanced capabilities",
        "technical deliverables",
        "deliverables",
        "outputs",
        "what you deliver",
    ),
    "success_metrics": ("success metrics", "success criteria", "metrics", "kpis"),
}

# Identity schema labels — not sellable skills
_IDENTITY_LABELS = frozenset(
    {
        "role",
        "personality",
        "memory",
        "experience",
        "style",
        "tone",
        "voice",
        "background",
        "identity",
        "name",
        "title",
    }
)

# Noise from OpenAPI / JSON / code fences mistakenly treated as bullets
_CAP_REJECT = re.compile(
    r"^(\{|\[|\}|\]|name|in|type|schema|required|properties|description|"
    r"parameters|items|enum|default|example|format|\$ref|"
    r"design|define|build|establish|generate|identify|determine|find|focus|"
    r"use|screen|create|write|make|add|set|get|run|start|stop|open|close)$",
    re.I,
)

# Single-token imperatives / vague nouns that pollute match
_NOISE_CAPS = frozenset(
    {
        "design",
        "define",
        "build",
        "establish",
        "generate",
        "identify",
        "determine",
        "find",
        "focus",
        "approach",
        "data",
        "multi",
        "tool access matrix (example)",
        "scope tokens",
        "sandboxing",
        "audit log",
        "job profiles",
        "default requirement",
        "mitigations",
        "failure mode",
    }
)



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


def _strip_fenced_code(text: str) -> str:
    """Drop ```...``` blocks so OpenAPI/YAML samples don't become capabilities."""
    return re.sub(r"```.*?```", "\n", text, flags=re.S)


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
    # Exact / boundary match first, then substring
    for alias in aliases:
        for key, val in sections.items():
            if key == alias or key.startswith(alias + " ") or key.endswith(" " + alias):
                return val
    for alias in aliases:
        for key, val in sections.items():
            if alias in key:
                return val
    return None


def _slugify(name: str) -> str:
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def _clean_cap(raw: str) -> str | None:
    label = raw.strip().strip("*").strip("`").strip().strip('"').strip("'")
    label = re.sub(r"[\r\n]+", " ", label)
    label = re.sub(r"\s+", " ", label)
    if not label or len(label) < 2:
        return None
    # Drop "- **Role**: full text" → prefer the value after colon when label is identity
    if ":" in label:
        head, tail = label.split(":", 1)
        head_l = head.strip().lower()
        if head_l in _IDENTITY_LABELS:
            # Use value only if it looks like a skill phrase (not a long bio)
            val = tail.strip()
            if 3 <= len(val) <= 80 and not val.lower().startswith("you "):
                # Prefer noun-phrase slice before first comma for long roles
                label = val.split(",")[0].strip()
            else:
                return None
        else:
            label = head.strip()
    low = label.lower()
    if low in _IDENTITY_LABELS or low in _NOISE_CAPS:
        return None
    if _CAP_REJECT.match(label):
        return None
    if label.startswith("{") or label.startswith("["):
        return None
    # Reject truncated / broken fragments
    if label.endswith(("(", "-", "—", ",")) or label.startswith(('"', "'")):
        return None
    if label.count("(") != label.count(")"):
        return None
    words = label.split()
    # Prefer multi-word skills; allow known short brand/tools (2+ chars with capital / acronym)
    if len(words) == 1 and (len(label) < 4 or (len(label) < 12 and not label.isupper() and label[0].islower())):
        return None
    if len(words) == 1 and label.lower() in {"spec", "api", "sdk", "data", "code", "docs"}:
        return None
    # Skill labels are short noun phrases — not prose sentences
    if len(words) > 7 or len(label) > 55:
        return None
    return label


def _dedupe_caps(caps: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for c in caps:
        key = c.lower()
        if key in seen or key in _NOISE_CAPS:
            continue
        seen.add(key)
        out.append(c)
        if len(out) >= 8:
            break
    return out


def _capabilities_from_text(text: str | None, *, allow_identity_fallback: bool = False) -> list[str]:
    if not text:
        return []
    text = _strip_fenced_code(text)
    caps: list[str] = []
    seen: set[str] = set()
    for line in text.splitlines():
        stripped = line.strip()
        # Only top-level markdown bullets (indent < 4) — skip nested OpenAPI lists
        if line[:1].isspace() and (len(line) - len(line.lstrip(" "))) >= 4:
            continue
        # Prefer **Label** bullets first (Agency style)
        m2 = re.match(r"^[-*]\s+\*\*([^*]+)\*\*", stripped)
        if m2:
            cand = _clean_cap(m2.group(1))
        else:
            m = re.match(
                r"^[-*]\s+(?:\*\*|__)?(.+?)(?:\*\*|__)?(?:\s*[—\-–:].*)?$",
                stripped,
            )
            if not m:
                continue
            cand = _clean_cap(m.group(1))
        if not cand:
            continue
        if not allow_identity_fallback and cand.lower() in _IDENTITY_LABELS:
            continue
        key = cand.lower()
        if key in seen:
            continue
        seen.add(key)
        caps.append(cand[:80])
        if len(caps) >= 8:
            break
    return _dedupe_caps(caps)


def _bold_labels(text: str | None) -> list[str]:
    """Extract **Label** markers from mission/body (Agency channel & skill headings)."""
    if not text:
        return []
    text = _strip_fenced_code(text)
    caps: list[str] = []
    seen: set[str] = set()
    for m in re.finditer(r"\*\*([^*]{2,60})\*\*", text):
        cand = _clean_cap(m.group(1))
        if not cand or cand.lower() in _IDENTITY_LABELS:
            continue
        key = cand.lower()
        if key in seen:
            continue
        seen.add(key)
        caps.append(cand[:80])
        if len(caps) >= 8:
            break
    return _dedupe_caps(caps)


def _capabilities_from_mission(mission: str | None) -> list[str]:
    """Last-resort noun phrases from mission (no Role/Personality junk)."""
    if not mission:
        return []
    # Pull Title Case or quoted skill-like fragments
    bits = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})\b", mission)
    out: list[str] = []
    seen: set[str] = set()
    for b in bits:
        low = b.lower()
        if low in _IDENTITY_LABELS or len(b) < 4:
            continue
        if low in seen:
            continue
        seen.add(low)
        out.append(b)
        if len(out) >= 4:
            break
    return out


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

    caps = _dedupe_caps(
        _capabilities_from_text(deliverables)
        or _bold_labels(deliverables)
        or _bold_labels(mission)
        or _capabilities_from_text(mission)
        or _bold_labels(workflow)
        or _capabilities_from_text(workflow)
        or _capabilities_from_mission(mission)
        or _capabilities_from_text(description)
        or ([div.replace("-", " ").title()] if div else [])
    )
    if not caps:
        caps = [div.replace("-", " ").title()] if div else ["Marketplace Service"]

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
        "skills": [
            {
                "id": _slugify(c) or f"skill-{i}",
                "name": c,
                "description": c,
                "tags": [div] if div else [],
                "inputModes": ["text", "application/json"],
                "outputModes": ["text", "application/json"],
            }
            for i, c in enumerate(caps[:8])
        ],
    }

    # Relative path under snapshot/ when possible
    source = str(path).replace("\\", "/")
    for marker in ("/snapshot/", "snapshot/"):
        if marker in source:
            source = source.split(marker, 1)[1]
            break

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
        source_path=source,
        sellable_capabilities=caps,
        catalog_products=catalog,
        agent_card=agent_card,
        raw_frontmatter=meta,
    )


def discover_personas(snapshot_root: Path) -> list[Path]:
    return sorted(snapshot_root.glob("*/*.md"))
