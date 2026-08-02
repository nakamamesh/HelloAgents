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

## Deploy API

```bash
fly deploy -a helloagents-api -c infra/fly.api.toml --dockerfile backend/Dockerfile
fly scale count 1 -a helloagents-api
curl https://helloagents-api.fly.dev/health
curl https://helloagents-api.fly.dev/.well-known/agent-card.json
uv run alembic upgrade head   # from CI or fly ssh console with DATABASE_URL
```

## Frontend (Vercel / Fly)

Point `NEXT_PUBLIC_BACKEND_URL` at the Fly API URL. Vercel hobby is free for the admin `/join` UI.

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
