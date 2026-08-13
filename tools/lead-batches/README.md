# Lead-batch email enrich fix (VMP + NOW)

## Problem
Maps scrapes run with `EMAIL=0` (by design). Emails come only from `enrich_websites.py`.
With `EMAIL_ENRICH_EVERY=25`, enrich never fired while NOW was ~10/164 → **hundreds of websites, 0 emails**.
Cloned enrich may also still reference the CRM `crm` table.

## Fix (run on the Mac that hosts the scrapers)

```bash
cd ~/HelloAgents
git fetch origin cursor/fix-vmp-now-email-enrich-54c9
git checkout cursor/fix-vmp-now-email-enrich-54c9 -- tools/lead-batches
bash tools/lead-batches/apply_email_enrich_fix.sh
```

Or one-liner from this branch after push:

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/nakamamesh/HelloAgents/cursor/fix-vmp-now-email-enrich-54c9/tools/lead-batches/apply_email_enrich_fix.sh)
```

(If curl one-liner: also need `enrich_websites.py` beside the script — prefer the git checkout form.)

## What it does
1. Installs hardened `enrich_websites.py` into `~/.cursor/skills/{now,vmp}/scripts/`
2. Speed: `DEPTH=1` `STABLE_SEC=45` `TIMEOUT_SEC=480` `MAPS_YIELD_SEC=5` `EMAIL_ENRICH_EVERY=5`
3. Reloads LaunchAgents and kicks statewide so new env applies (does **not** kill peer Maps containers)
4. Immediately background-enriches existing CSVs (no Docker; safe alongside Maps)
5. 15‑min enrich LaunchAgent
6. Does **not** freeze empty emails

## Verify
```bash
tail -f ~/.cursor/skills/now/data/enrich_console.log
python3 ~/.cursor/skills/now/scripts/status.py
python3 ~/.cursor/skills/vmp/scripts/status.py
```
