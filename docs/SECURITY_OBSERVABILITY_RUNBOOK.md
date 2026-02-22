# Security Observability Runbook (Phase 5)

_Last updated: 2026-02-22 (UTC)_

## Purpose
Operational playbook for local/staging/production response when `/health/` indicates degraded security-critical platform conditions (DB/cache/Celery/Redis queue).

## Signals and thresholds
Source of truth: admin-authenticated `GET /health/` diagnostics.

### Celery alert kinds
- `celery_active_tasks_high`
  - Trigger: `active_tasks >= HEALTH_ALERT_ACTIVE_TASKS_THRESHOLD`.
  - Immediate risk: backlog growth, delayed async moderation/scan jobs.
- `celery_scheduled_tasks_high`
  - Trigger: `scheduled_tasks >= HEALTH_ALERT_SCHEDULED_TASKS_THRESHOLD`.
  - Immediate risk: delayed execution windows and SLA drift.
- `celery_reserved_tasks_high`
  - Trigger: `reserved_tasks >= HEALTH_ALERT_RESERVED_TASKS_THRESHOLD`.
  - Immediate risk: worker saturation and uneven queue drain.

### Redis queue alert kind
- `redis_queue_depth_high`
  - Trigger: queue length for any name in `HEALTH_REDIS_QUEUE_NAMES` is `>= HEALTH_ALERT_REDIS_QUEUE_DEPTH_THRESHOLD`.
  - Immediate risk: unbounded queue growth, delayed malware scan/moderation tasks.

## Triage steps (first 10 minutes)
1. Confirm whether issue is transient (3 checks, 30–60s apart).
2. Check worker liveness and concurrency.
3. Check Redis connectivity/latency.
4. Check API error/latency trend (`X-Response-Time-Ms` and slow-request warnings).

## Command checks
Use from backend host/container context.

```bash
# 1) Health baseline (admin-authenticated request in real environments)
curl -sS http://localhost:8000/health/

# 2) Celery workers
celery -A ZuntoProject inspect active
celery -A ZuntoProject inspect scheduled
celery -A ZuntoProject inspect reserved

# 3) Queue depths (default queue names)
redis-cli LLEN celery

# 4) API slow warnings / timing samples (example)
# Check app logs for warning-level slow-request entries.
```

## Response matrix

### A) Worker down / `celery-check-failed` / `no-active-workers`
- Restart Celery workers.
- If repeat failures, reduce non-critical async job producers temporarily.
- Verify queue drain trend after restart.

### B) Queue depth high but workers alive
- Increase worker concurrency (temporary scale-out).
- Prioritize security queues first (malware scan/moderation) if queue separation exists.
- Investigate producer spikes (bot floods, upload abuse, retry loops).

### C) Cache degraded / Redis unavailable
- Enable degraded-mode messaging to operators.
- Shift to fail-safe behavior for sensitive endpoints (throttle tighter, protect checkout/auth).
- Restore Redis and verify queue consistency before normalization.

## Security-specific guidance for this marketplace
Given marketplace focus (niche handmade materials + second-hand goods + verified seller trust boundaries):
- During abuse spikes, prioritize moderation and malware pipelines over non-critical analytics jobs.
- Escalate verified-seller impersonation and repeated relist abuse events to manual review quickly.

## Exit criteria (incident closed)
- `/health/` returns `healthy` for 3 consecutive checks.
- Alert kinds cleared from diagnostics.
- Queue depth back below threshold with downward trend.
- No sustained p95/p99 latency regression in critical auth/checkout paths.

## Follow-up actions
- Record incident timeline and root cause.
- Tune thresholds if noise/under-sensitivity is observed.
- Convert repeated manual mitigation into automation (remaining Phase 5 objective).
