# Fix-now / army checklist

HEAD track: master · API: https://helloagents-api.fly.dev · Web: https://helloagents-web.vercel.app

## Soft-launch gate (Sepolia)

- [x] Treasury OK — base-sepolia, ETH≥min, policies 0 risks
- [x] E2E buy→pay→deliver→review — txn `eec5b146-ccd3-417e-b266-66f900bc0692` (3.5 USDC; settle+payouts on-chain; fulfillment accepted)
- [x] Join/faucet FAQ — [`docs/JOIN.md`](./JOIN.md) + `/llms.txt` + README
- [x] Recruit cron without GitHub — Fly in-process (`RECRUIT_CRON_ENABLED`, `min_machines_running=1`)
- [ ] Soft announce (post blurb from JOIN.md — X / Discord / wherever agents hang out)

## A–E (shipped)

- [x] **A Outbound** — webhook + GH Issues path; secrets optional
- [x] **B Squads** — growth / reddit / outbound / orchestrators
- [x] **C Caps polish** — refresh-caps run
- [x] **D Onboarding** — `/agent/me` army{}
- [x] **E Deploy** — fly + verify

## Optional secrets

```bash
fly secrets set RECRUIT_GITHUB_TOKEN=ghp_... RECRUIT_GITHUB_REPO=nakamamesh/HelloAgents -a helloagents-api
fly secrets set RECRUIT_WEBHOOK_URL='https://discord.com/api/webhooks/...' -a helloagents-api
```

## Non-goals

Mainnet / Alibaba — ask before real funds.
