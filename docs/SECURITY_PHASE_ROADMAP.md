# Zunto Security & Scalability Remediation Roadmap

## Phase 1 — Auth/role/endpoint hardening
Completed incrementally.

## Phase 2 — Sensitive endpoint throttling and abuse controls
Completed incrementally.

## Phase 3 — Upload and chat safety pipeline
In progress (MIME checks and anti-phishing guardrails done; synchronous malware scanning + quarantine fallback now added for media validation; async scan pipeline and release workflow pending).

## Phase 4 — Seller/admin permission closure and auditability
In progress (seller-only endpoint enforcement added for market/orders; admin moderation queue/detail APIs for product reports with status-transition enforcement and audit events are now added; broader cross-domain admin audit logging remains pending).

## Phase 5 — Scalability and observability hardening
In progress (hot-path write amplification reduced for product views, statistics query consolidation applied in orders/reviews, public review stats endpoints throttled, favorite counter updates made DB-atomic, product stats endpoint cached/DB-portable with mutation-triggered cache invalidation, and product-view product+user index added; broader queue observability and runtime dashboards still pending).

## Phase 6 — Object storage migration (free-tier first)
- **Recommendation:** move media/blob payloads from local filesystem/DB pathways to object storage using a free-tier provider during early rollout.
- **Current implementation in this phase:** optional object storage settings and S3-compatible backend wiring guarded by `USE_OBJECT_STORAGE`.
- **Free-tier note:** start with free tier for dev/staging and controlled production traffic, then upgrade as egress/request volume grows.
- **Next steps:** signed direct uploads, async AV scanning, quarantine and release workflow, CDN fronting, lifecycle retention rules.
