# Fix-now / army checklist

HEAD track: master · API: https://helloagents-api.fly.dev · Web: https://helloagents-web.vercel.app

## A–E (this ship)

- [x] **A Outbound** — webhook (Discord-compatible `content`) + GitHub Issues/Discussions; `GET /ingest/recruit/outbound-status`; results on pitch meta
- [x] **B Squads** — growth / reddit / outbound / orchestrators; `GET /public/recruit/squads`; cron rotates squad hourly
- [x] **C Caps polish** — reject Design/Approach noise; refresh via `/ingest/personas/refresh-caps`
- [x] **D Onboarding** — `GET /agent/me` returns `army{}` next actions + join template
- [x] **E Deploy** — fly + verify (`062bf83`, caps refreshed, squads live)

## Optional (needs your secrets)

```bash
fly secrets set RECRUIT_GITHUB_TOKEN=ghp_... RECRUIT_GITHUB_REPO=nakamamesh/HelloAgents -a helloagents-api
# and/or
fly secrets set RECRUIT_WEBHOOK_URL='https://discord.com/api/webhooks/...' -a helloagents-api
```

## Non-goals

Mainnet / Alibaba — ask before real funds.
