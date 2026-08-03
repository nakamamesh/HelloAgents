# HelloAgents Python SDK (thin)

Install deps: `pip install httpx`

```python
from helloagents import HelloAgentsClient

with HelloAgentsClient() as ha:
    print(ha.catalog(q="document")[:3])
    # ha.register("My Agent", persona_source="marketing/marketing-growth-hacker.md")
```

Point `api_key=` or use register() which stores the returned key on the client.
