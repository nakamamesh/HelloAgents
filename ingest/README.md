# Agency ingestion

Pinned CI snapshot of [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents)
(MIT) under `snapshot/`, commit in `snapshot/UPSTREAM_COMMIT`.

```bash
# Convert personas → JSON (no DB)
python convert_cli.py

# Seed DB (from backend/)
uv run python -m app.scripts.seed_marketplace
# or POST /ingest/seed with X-Admin-Key
```

`UPSTREAM_SYNC` audits land in `upstream_sync_audits`.
Wallet provisioning is Phase 3 (Turnkey) — seed agents may have `wallet_id=null` until secrets are set.
