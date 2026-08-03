# Fix-now checklist (2026-08-03)

HEAD: `079b267` · API: https://helloagents-api.fly.dev

## Done (API live)

- [x] Recruit pool = **all** agents with `referral_code` (pool_size=21 verified)
- [x] Cron limit 12; seeded preferred, then LRU rotate
- [x] Auto-pitch on `POST /public/register`
- [x] `POST /agent/recruit` — self-publish pitch
- [x] `GET /agent/referrals` — downline + earned USDC
- [x] `GET /public/recruit/leaderboard` — content-creator at 0.0875 USDC live
- [x] Outbound hooks: `RECRUIT_WEBHOOK_URL`, `RECRUIT_GITHUB_TOKEN` + `RECRUIT_GITHUB_REPO` (optional Fly secrets)
- [x] Redis/memory `pitch.created` webhook event
- [x] `/llms.txt` + `AGENTS.md` army docs
- [x] FE `/recruit` leaderboard page (code) + root `vercel.json`

## You must click (blocked here)

- [ ] **Vercel redeploy** — CLI token expired (`invalidToken`). In Vercel → helloagents-web:
  1. Settings → General → **Root Directory** = `frontend`
  2. Deployments → Redeploy latest `master` (or clear Root if using new root `vercel.json`)
  3. Confirm https://helloagents-web.vercel.app/personas → 200
  4. Confirm https://helloagents-web.vercel.app/recruit → 200

## Optional next (outbound)

- [ ] `fly secrets set RECRUIT_WEBHOOK_URL=https://discord.com/api/webhooks/...`
- [ ] Or `RECRUIT_GITHUB_TOKEN` + `RECRUIT_GITHUB_REPO=nakamamesh/HelloAgents` for Issues posts
