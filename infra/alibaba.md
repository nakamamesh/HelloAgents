# Alibaba Cloud Singapore migration (prep)

Target later: **ACK Serverless / SAE** in `ap-southeast-1`. Today: Fly `sin`.

## Why wait is OK

- Geography already Singapore-adjacent (`sin`).
- Product surface (API + Vercel web) is stable; no Aliyun secrets in repo yet.

## Checklist (when ready — pause for money/keys)

1. Create ACK/SAE app + managed Postgres + Redis in `ap-southeast-1`.
2. Port Dockerfile (already root `Dockerfile`) — container listens `0.0.0.0:8000`.
3. Set secrets (never commit): `DATABASE_URL` (asyncpg), `REDIS_URL`, `OPENROUTER_*`, `ADMIN_API_KEY`, `JWT_SECRET`, Turnkey trio, `WALLET_NETWORK`.
4. Run `alembic upgrade head` as release command.
5. Point `helloagents-api` DNS / Cloudflare to Alibaba LB.
6. Update CORS + frontend `BACKEND_URL` + GitHub recruit cron `HELLOAGENTS_URL`.
7. Re-apply Turnkey policies after any org change; fund treasury gas on target network.
8. Smoke: `/health`, `/public/catalog`, one Sepolia (or mainnet) buy.

## Non-goals now

- No live Alibaba billing / account wiring in this pass.
- Keep Fly until ACK smoke is green.
