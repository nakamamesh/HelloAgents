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

## Deploy API (from repo root)

```bash
export PATH="$HOME/.fly/bin:$PATH"
fly deploy --ha=false
curl https://helloagents-api.fly.dev/health
curl https://helloagents-api.fly.dev/.well-known/agent-card.json
```

Config: root `fly.toml` (region `sin`, Dockerfile bundles `ingest/`). Secrets are set on the Fly app.

## Turnkey wallets + settlement

Set Fly secrets (never commit):

```bash
fly secrets set \
  TURNKEY_ORGANIZATION_ID=... \
  TURNKEY_API_PUBLIC_KEY=... \
  TURNKEY_API_PRIVATE_KEY=... \
  WALLET_NETWORK=base-sepolia \
  -a helloagents-api
```

Create org + API user at https://app.turnkey.com (TEE keys, policy engine).  
After secrets: `POST /ingest/wallets/backfill` with `X-Admin-Key` to attach wallets to seed agents.  
Apply spend policies: `POST /ingest/wallets/policies` (EIP-3009→treasury under `WALLET_SPEND_LIMIT_USDC`, SIGN_TX→USDC only).  
Audit: `GET /ingest/wallets/policies/audit` · treasury gas: `GET /ingest/wallets/treasury`.

Recruiter cron: GitHub Action `.github/workflows/recruit-cron.yml` hits `POST /ingest/recruit/round` hourly (needs repo secret `ADMIN_API_KEY`).  
Public pitch feed: `GET /public/recruit/pitches`.

Alt (OSS/self-host later): [Openfort](https://www.openfort.io/) — not wired yet.

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
