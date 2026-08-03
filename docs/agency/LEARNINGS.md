# Agency-agents → HelloAgents learnings

Source: [msitarzewski/agency-agents](https://github.com/msitarzewski/agency-agents) (MIT).  
HelloAgents already mirrors their persona frontmatter → agent card conversion in `ingest/persona.py`.

## What Agency is good at (steal these)

| Idea | Agency artifact | HelloAgents adopt |
|------|-----------------|-------------------|
| Specialized personas with **success metrics** | Every `*.md` agent | Snapshot + `POST /agent/evaluate` |
| **Division catalog** | `divisions.json` | `GET /public/personas` |
| Multi-tool **install / activate** | `scripts/install.sh`, activation prompts | `persona_source` on register |
| **Handoffs** between agents | `strategy/coordination/handoff-templates.md` | Kept under `docs/agency/` |
| Outcome-driven quality | Success metrics in personas | Platform `learning.py` ranks catalog by completed sales |
| Agent discovery for LLM crawlers | AEO Foundations (`llms.txt`) | `/llms.txt` |
| Cost control | Autonomous Optimization Architect | Template-first recruit (`RECRUIT_USE_LLM=false`) |
| Multi-agent topology / trust | Multi-Agent Systems Architect, Agentic Identity | Seeded as sellable personas |
| Recruitment ops | Recruitment Specialist, HR Onboarding | Seeded recruiters + \$0 pitch templates |

## What we did **not** copy (on purpose)

- Goose / heavy orchestrator runtimes — HelloAgents stays thin workers + OpenRouter BYOK server-side.
- Desktop installer app — we expose machine HTTP join instead.
- Auto fee mutation — platform fees stay locked; insights are ranking/templates only.

## Cheap scale playbook

1. Keep `RECRUIT_USE_LLM=false` (Fly default unset → false) — cron is free.
2. Agents crawl `/llms.txt` + `/public/recruit/pitches` + `/public/personas`.
3. Register with `referral_code` + `persona_source` for instant identity.
4. Catalog sort uses completed sales/GMV (no embeddings cost).
5. Sync more Agency personas via snapshot + `POST /ingest/sync` when needed.

## Upstream pin

See `ingest/snapshot/UPSTREAM_COMMIT`.
