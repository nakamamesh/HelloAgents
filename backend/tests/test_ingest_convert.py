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
    assert p.sellable_capabilities or p.identity
