# Fly.io / Railway deploy notes

## Why Fly (Singapore)
- Cheap shared VMs, auto-stop when idle  
- Region `sin` matches Alibaba target geography for later migration  
- HTTPS included  

## One-time setup

```bash
# install
curl -L https://fly.io/install.sh | sh
export PATH="$HOME/.fly/bin:$PATH"

fly auth login
cd /path/to/HelloAgents

# create app + Postgres + Redis (prompts OK)
fly apps create helloagents-api
fly postgres create --name helloagents-db --region sin --initial-size shared-cpu-1x
fly postgres attach helloagents-db -a helloagents-api
fly redis create --name helloagents-redis --region sin
# attach redis URL manually as REDIS_URL secret if prompted

fly secrets set -a helloagents-api \
  OPENROUTER_API_KEY=sk-or-... \
  ADMIN_API_KEY="$(openssl rand -hex 24)" \
  JWT_SECRET="$(openssl rand -hex 32)"
```

Note: Fly Postgres gives `DATABASE_URL` as `postgres://...`. Convert for async SQLAlchemy:

```
postgresql+asyncpg://USER:PASS@HOST:5432/DB
```

Set that as secret `DATABASE_URL` if the attached URL lacks `+asyncpg`.

# Fly.io / Railway deploy notes

## Deploy API (from repo root)

```bash
export PATH="$HOME/.fly/bin:$PATH"
fly deploy --ha=false
curl https://helloagents-api.fly.dev/health
curl https://helloagents-api.fly.dev/.well-known/agent-card.json
```

Config: root `fly.toml` (region `sin`, Dockerfile bundles `ingest/`). Secrets are set on the Fly app.

## CDP wallets (Phase 3)

Set Fly secrets (never commit):

```bash
fly secrets set \
  CDP_API_KEY_ID=... \
  CDP_API_KEY_SECRET=... \
  CDP_WALLET_SECRET=... \
  CDP_NETWORK=base-sepolia \
  -a helloagents-api
```

Optional: `CDP_ACCOUNT_POLICY_ID` from CDP Portal (per-tx / daily caps + allowlist).  
After secrets: `POST /ingest/wallets/backfill` with `X-Admin-Key` to attach wallets to seed agents.

## Cost ballpark
Idle API + small Postgres: often **~$5–25/mo**. Scale to zero API when unused.

## Railway alternative
```bash
railway login
railway init
railway add --database postgres
railway add --database redis
railway up
```
Use `infra/railway.toml` if present.
