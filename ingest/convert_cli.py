from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from persona import convert_to_helloagents, discover_personas  # noqa: E402


def main() -> None:
    snapshot = ROOT / "snapshot"
    personas = [convert_to_helloagents(p) for p in discover_personas(snapshot)]
    out = ROOT / "snapshot" / "converted.json"
    out.write_text(json.dumps([p.to_dict() for p in personas], indent=2), encoding="utf-8")
    print(f"converted={len(personas)} out={out}")
    for p in personas:
        print(f"- {p.division}/{p.name} caps={len(p.sellable_capabilities)}")


if __name__ == "__main__":
    main()
