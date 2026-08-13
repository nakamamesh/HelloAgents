# Rebuild VMP + NOW the CRM way

Clones `~/.cursor/skills/crm/` on **your Mac** into `now` and `vmp` skills, with classic CRM speed (`DEPTH=2`, `EMAIL_ENRICH_EVERY=25`, `STABLE_SEC=60`, `TIMEOUT_SEC=600`, `CONCURRENCY=8`, `DOCKER_MEM=3500m`). Uses CRM’s `enrich_websites.py` (renamed), not a separate enrich.

Requires Darwin and `~/.cursor/skills/crm/scripts/enrich_websites.py`.

## One-liner (curl | bash)

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/nakamamesh/HelloAgents/cursor/vmp-now-crm-clone-54c9/tools/crm-clone/rebuild_vmp_now_from_crm.sh)
```

Places files are fetched from the same branch if they are not next to the script.

## Git checkout

```bash
cd ~/HelloAgents
git fetch origin cursor/vmp-now-crm-clone-54c9
git checkout cursor/vmp-now-crm-clone-54c9 -- tools/crm-clone
bash tools/crm-clone/rebuild_vmp_now_from_crm.sh
```

## What it does

1. Aborts unless macOS + CRM enrich exists
2. For `now` then `vmp`: backup existing skill, copy all CRM scripts, rename identifiers, install `places_*.py` as `places.py`, write `SKILL.md`
3. Fresh start: truncate `places_done.txt`, remove `enrich_done.txt` / `places_empty.txt`, backup-then-remove `{batch}.db` and combined CSV
4. Install LaunchAgents `com.helloagents.{now,vmp}.{watchdog,keeper}` (caffeinate `-dims`, KeepAlive)
5. bootout old agents, then bootstrap + enable
6. Print `status.py` for both

Does not kill peer Maps containers. Watchdogs serialize Docker with `vmp-scraper-|now-scraper-` and existing peers.

## Status

```bash
python3 ~/.cursor/skills/now/scripts/status.py
python3 ~/.cursor/skills/vmp/scripts/status.py
```
