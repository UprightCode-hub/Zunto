# Zunto Security & Scalability Remediation Roadmap

## Phase 1 — Auth/role/endpoint hardening
Completed incrementally.

## Phase 2 — Sensitive endpoint throttling and abuse controls
Completed incrementally (including payment callback host validation on initialize flow).

## Phase 3 — Upload and chat safety pipeline
In progress (MIME checks and anti-phishing guardrails done; synchronous malware scanning + quarantine fallback now added for media validation; async scan pipeline and release workflow pending).

## Phase 4 — Seller/admin permission closure and auditability
In progress (seller-only endpoint enforcement added for market/orders; admin moderation queue/detail APIs for product reports with status-transition enforcement, moderator attribution, and audit events are now added; admin audit coverage now also includes staff access to seller-order list/detail views, admin refund-processing actions, bulk refund decision endpoint coverage, assistant admin observability views (logs/reports/metrics), dashboard admin analytics read paths, and a company-admin operations summary endpoint for frontend queue triage; refund webhook lifecycle handling was hardened for pending/processing states; broader cross-domain admin audit logging still remains).

## Phase 5 — Scalability and observability hardening
In progress (hot-path write amplification reduced for product views, statistics query consolidation applied in orders/reviews, public review stats endpoints throttled, favorite counter updates made DB-atomic, product stats endpoint cached/DB-portable with mutation-triggered cache invalidation, product-view product+user index added, and `/health/` now exposes admin-only Celery queue diagnostics while keeping public output minimal; request-latency header + slow-API warning logging middleware added; missing `CookieJWTAuthentication` module was restored for DRF auth bootstrap stability; scheduled backend health-monitor logging task added; broader runtime dashboards and external alert routing automation still pending).

## Phase 6 — Object storage migration (free-tier first)
- **Recommendation:** move media/blob payloads from local filesystem/DB pathways to object storage using a free-tier provider during early rollout.
- **Current implementation in this phase:** optional object storage settings and S3-compatible backend wiring guarded by `USE_OBJECT_STORAGE`.
- **Free-tier note:** start with free tier for dev/staging and controlled production traffic, then upgrade as egress/request volume grows.
- **Next steps:** signed direct uploads, async AV scanning, quarantine and release workflow, CDN fronting, lifecycle retention rules.


## Continuation handoff
See `docs/SECURITY_CONTINUATION_HANDOFF.md` for latest implementation state, pending backlog, and next-session startup checklist.

## Phase 5 runbook
See `docs/SECURITY_OBSERVABILITY_RUNBOOK.md` for alert thresholds, triage commands, and incident response actions for `/health/` diagnostics.

## 10k concurrency/adversarial test strategy
See `docs/SECURITY_10K_BOT_DEFENSE_PLAN.md` for phased local validation guidance targeting ~10k simultaneous users under mixed legitimate and hostile traffic.

## Company-admin frontend parity plan
See `docs/ADMIN_COMPANY_PORTAL_PARITY_NEXT_SESSION.md` for Django-admin vs frontend operations parity scope and next-session implementation order.
