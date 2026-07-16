# agentops-cloud (Python SDK)

`pip install agentops-cloud`

Not implemented yet — this package exists so the install name and import
path are reserved ahead of Phase 2 (SDK) of the roadmap. See
`/docs/Roadmap.md` and `/docs/FutureVision.md`.

Planned surface:

```python
import agentops_cloud as ao

ao.init(api_key="...")       # registers this process as a discovered agent
ao.heartbeat()                # periodic liveness signal
ao.track_cost(tokens=..., model=...)
ao.track_tool_call(name=...)
```
