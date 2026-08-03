from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "ingest"))

from persona import convert_to_helloagents


def test_convert_growth_hacker():
    path = ROOT / "ingest/snapshot/marketing/marketing-growth-hacker.md"
    p = convert_to_helloagents(path)
    assert p.name == "Growth Hacker"
    assert p.emoji
    assert p.agent_card["tools"]
    assert any(t["name"] == "buy" for t in p.agent_card["tools"])
    assert p.sellable_capabilities
    assert "Role" not in p.sellable_capabilities
    assert "Personality" not in p.sellable_capabilities


def test_recruitment_specialist_not_identity_labels():
    path = ROOT / "ingest/snapshot/specialized/recruitment-specialist.md"
    p = convert_to_helloagents(path)
    bad = {"Role", "Personality", "Memory", "Experience"}
    assert not bad.intersection(p.sellable_capabilities), p.sellable_capabilities


def test_api_platform_engineer_no_brace_caps():
    path = ROOT / "ingest/snapshot/engineering/engineering-api-platform-engineer.md"
    p = convert_to_helloagents(path)
    assert not any(c.startswith("{") for c in p.sellable_capabilities), p.sellable_capabilities
    assert p.sellable_capabilities
