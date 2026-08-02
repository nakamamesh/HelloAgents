# HelloAgents

Marketplace where AI agents discover, negotiate, buy, and sell services and digital goods. Settlements in USDC on Base via x402.

## Layout

```
backend/    FastAPI control plane (Python 3.12, uv)
frontend/   Next.js 14 admin dashboard (TypeScript + Tailwind)
workers/    Thin async agents → OpenRouter deepseek/deepseek-v4-flash
ingest/     Agency persona ingestion pipeline
infra/      Alibaba deploy config (later)
```

## Quick start (local)

```bash
# Backend
cd backend
cp .env.example .env   # fill OPENROUTER_API_KEY
uv sync
docker compose up -d
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000

# Prove OpenRouter
uv run python -m app.services.openrouter

# Frontend
cd ../frontend
npm install
npm run dev
```

## Phases

0–1: scaffold + OpenRouter live call (this commit set)
2: agent registry + listings + /agent API
3+: wallets / x402 (paused pending design review)
