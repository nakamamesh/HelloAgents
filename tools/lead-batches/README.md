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
2. Sets `EMAIL_ENRICH_EVERY=5` in watchdog/statewide/plists
3. Immediately background-enriches existing CSVs (no Docker; safe alongside Maps)
4. Does **not** freeze empty emails — retries any website row with blank email

## Verify
```bash
tail -f ~/.cursor/skills/now/data/enrich_console.log
python3 ~/.cursor/skills/now/scripts/status.py
python3 ~/.cursor/skills/vmp/scripts/status.py
```
