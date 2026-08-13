#!/usr/bin/env python3
"""Patch VMP/NOW skills for faster Maps + earlier email enrich.

Safe: does not kill peer Maps containers. Restarts only this batch's
run_statewide.py so LaunchAgent watchdog respawns with new env.
"""
from __future__ import annotations

import os
import plistlib
import re
import subprocess
import sys
from pathlib import Path

HOME = Path.home()
SPEED = {
    "DEPTH": "1",
    "RURAL_DEPTH": "1",
    "STABLE_SEC": "45",
    "TIMEOUT_SEC": "480",
    "INACTIVITY": "45s",
    "EMAIL_ENRICH_EVERY": "5",
    "MAPS_YIELD_SEC": "5",
    "CONCURRENCY": "8",
    "COUNTY_TIMEOUT": "900",
}


def patch_text(path: Path, batch: str) -> None:
    if not path.exists():
        return
    t = path.read_text(encoding="utf-8")
    orig = t
    # defaults in python
    t = re.sub(r'EMAIL_ENRICH_EVERY",\s*"\d+"', 'EMAIL_ENRICH_EVERY", "5"', t)
    t = re.sub(r'MAPS_YIELD_SEC",\s*"\d+"', 'MAPS_YIELD_SEC", "5"', t)
    t = re.sub(r'YIELD_SEC = int\(os\.environ\.get\("MAPS_YIELD_SEC", "\d+"\)\)',
               'YIELD_SEC = int(os.environ.get("MAPS_YIELD_SEC", "5"))', t)
    t = t.replace('os.environ.get("DEPTH", "2")', 'os.environ.get("DEPTH", "1")')
    t = t.replace('os.environ.get("RURAL_DEPTH", "1")', 'os.environ.get("RURAL_DEPTH", "1")')
    t = t.replace('os.environ.get("STABLE_SEC", "60")', 'os.environ.get("STABLE_SEC", "45")')
    t = t.replace('os.environ.get("TIMEOUT_SEC", "600")', 'os.environ.get("TIMEOUT_SEC", "480")')
    t = t.replace('os.environ.get("INACTIVITY", "60s")', 'os.environ.get("INACTIVITY", "45s")')
    t = t.replace('COUNTY_TIMEOUT", "1100"', 'COUNTY_TIMEOUT", "900"')
    t = t.replace('COUNTY_TIMEOUT", "1800"', 'COUNTY_TIMEOUT", "900"')
    # bash ${VAR:-n}
    t = re.sub(r'EMAIL_ENRICH_EVERY:-25', "EMAIL_ENRICH_EVERY:-5", t)
    t = re.sub(r'DEPTH:-2', "DEPTH:-1", t)
    t = re.sub(r'STABLE_SEC:-60', "STABLE_SEC:-45", t)
    t = re.sub(r'TIMEOUT_SEC:-600', "TIMEOUT_SEC:-480", t)
    t = re.sub(r'INACTIVITY:-60s', "INACTIVITY:-45s", t)
    t = re.sub(r'COUNTY_TIMEOUT:-1100', "COUNTY_TIMEOUT:-900", t)
    t = re.sub(r'COUNTY_TIMEOUT:-1800', "COUNTY_TIMEOUT:-900", t)
    t = re.sub(r'MAPS_YIELD_SEC:-25', "MAPS_YIELD_SEC:-5", t)
    if "MAPS_YIELD_SEC" not in t and path.suffix == ".sh" and "watchdog" in path.name:
        t = t.replace(
            f'export {batch.upper()}_DOCKER_MEM=',
            'export MAPS_YIELD_SEC="${MAPS_YIELD_SEC:-5}"\nexport '
            + f'{batch.upper()}_DOCKER_MEM=',
        )
    if t != orig:
        path.write_text(t, encoding="utf-8")
        print("patched", path)


def patch_plist(path: Path, prefix: str) -> None:
    if not path.exists():
        return
    with path.open("rb") as f:
        data = plistlib.load(f)
    env = data.setdefault("EnvironmentVariables", {})
    env.update(SPEED)
    env["HOME"] = str(HOME)
    env.setdefault("PATH", "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin")
    env[f"{prefix}_CSV"] = str(HOME / f"HelloAgents/{prefix.lower()}/{prefix.lower()}.csv")
    env[f"{prefix}_DB"] = str(HOME / f".cursor/skills/{prefix.lower()}/data/{prefix.lower()}.db")
    env[f"{prefix}_DOCKER_MEM"] = env.get(f"{prefix}_DOCKER_MEM", "3500m")
    with path.open("wb") as f:
        plistlib.dump(data, f, sort_keys=False)
    print("patched plist", path)


def reload_launchagent(label: str, plist: Path) -> None:
    uid = os.getuid()
    target = f"gui/{uid}/{label}"
    subprocess.run(["launchctl", "bootout", target], check=False, capture_output=True)
    if plist.exists():
        subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", str(plist)], check=False)
        subprocess.run(["launchctl", "enable", target], check=False)
        print("reloaded", label)


def kick_statewide(batch: str) -> None:
    # Let watchdog respawn with new env; do NOT docker rm peers
    subprocess.run(
        ["pkill", "-f", f"{batch}/scripts/run_statewide.py"],
        check=False,
    )
    print(f"kicked {batch} statewide (watchdog will restart)")


def email_count(batch: str) -> str:
    db = HOME / f".cursor/skills/{batch}/data/{batch}.db"
    csvp = HOME / f"HelloAgents/{batch}/{batch}.csv"
    if db.exists():
        import sqlite3

        conn = sqlite3.connect(str(db))
        try:
            n = conn.execute(f"SELECT COUNT(*) FROM {batch}").fetchone()[0]
            e = conn.execute(
                f"SELECT COUNT(*) FROM {batch} WHERE IFNULL(email,'')!=''"
            ).fetchone()[0]
            w = conn.execute(
                f"SELECT COUNT(*) FROM {batch} WHERE IFNULL(website,'')!=''"
            ).fetchone()[0]
            return f"{batch}: db_rows={n} email={e} website={w}"
        except Exception as ex:
            return f"{batch}: db err {ex}"
        finally:
            conn.close()
    if csvp.exists():
        import csv

        rows = email = web = 0
        with csvp.open(newline="", encoding="utf-8", errors="replace") as f:
            for r in csv.DictReader(f):
                rows += 1
                if (r.get("email") or "").strip():
                    email += 1
                if (r.get("website") or "").strip():
                    web += 1
        return f"{batch}: csv_rows={rows} email={email} website={web}"
    return f"{batch}: no db/csv yet"


def main() -> int:
    for batch, prefix in (("now", "NOW"), ("vmp", "VMP")):
        skill = HOME / f".cursor/skills/{batch}"
        if not skill.exists():
            print("SKIP missing", skill)
            continue
        for name in ("run_statewide.py", "watchdog.sh", "keeper.sh", "run_scrape.sh"):
            patch_text(skill / "scripts" / name, batch)
        pl_dir = HOME / "Library/LaunchAgents"
        patch_plist(pl_dir / f"com.helloagents.{batch}.watchdog.plist", prefix)
        patch_plist(pl_dir / f"com.helloagents.{batch}.keeper.plist", prefix)
        reload_launchagent(f"com.helloagents.{batch}.watchdog", pl_dir / f"com.helloagents.{batch}.watchdog.plist")
        reload_launchagent(f"com.helloagents.{batch}.keeper", pl_dir / f"com.helloagents.{batch}.keeper.plist")
        kick_statewide(batch)
        print(email_count(batch))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
