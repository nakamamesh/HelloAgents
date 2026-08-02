# Thin workers

```bash
# from repo root, with backend/.env loaded for OPENROUTER_API_KEY
cd backend && uv run python ../workers/worker.py \
  --api-key "$AGENT_API_KEY" \
  --task "Propose one growth experiment for HelloAgents"
```

No Goose / no third-party orchestrator. Workers call OpenRouter directly.
