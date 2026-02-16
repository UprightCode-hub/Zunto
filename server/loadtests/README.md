# Load Testing (10K Readiness)

## Assistant + Report Burst (Locust)

```bash
locust -f server/loadtests/assistant_locustfile.py --host http://localhost:8000
```

Track:
- p95/p99 latency on `/assistant/api/chat/`
- throttle hit rates (429)
- error rates and timeout rates
- DB CPU + query latency

## WebSocket Stress
Use your preferred WS load tool (k6, artillery, or custom asyncio client) against:

`ws://localhost:8000/ws/chat/<conversation_id>/?token=<token>`

Track:
- concurrent connection ceilings
- dropped/broken sockets
- message fanout latency
- channel layer saturation (Redis)

## DB Profiling During Load

- Capture query counts per request endpoint
- Capture slow query logs
- Monitor memory and worker saturation

## Fallback Validation

During synthetic load, intentionally force:
- LLM API outage
- Redis restart
- DB read latency spike

Ensure assistant fallback responses and retry paths still succeed.
