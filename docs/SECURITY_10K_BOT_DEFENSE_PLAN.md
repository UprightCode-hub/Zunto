# Zunto 10k-Concurrency Bot/Hacker Defense Plan (Local Validation Focus)

_Last updated: 2026-02-22 (UTC)_

## Context
This plan translates the current remediation state into a practical security posture for an e-commerce workload targeting ~10,000 simultaneous users under likely bot pressure (credential stuffing, scraping, spam, checkout abuse, and opportunistic exploit traffic).

It is designed for **local validation first**, then straightforward production rollout.

## 1) Threat Model Priority (for current architecture)
1. **Auth abuse**: credential stuffing, password spray, OTP brute-force, token replay.
2. **Commerce abuse**: cart/checkout endpoint hammering, coupon abuse, payment callback spoofing.
3. **Content abuse**: malicious uploads, phishing links in chat/reviews, spam product/report submissions.
4. **Admin-targeted risk**: privilege misuse and low-audit mutations across admin domains.
5. **Availability attacks**: high-rate API floods, expensive-query amplification, queue backlogs.


## 1A) Marketplace Intent & Trust Boundaries (minute detail)
This platform is intentionally optimized for:
1. Sellers listing niche handmade/low-volume items (e.g., crocheting and knotting materials) that are hard to sell on large marketplaces.
2. Sellers listing second-hand/used products.
3. Verified sellers receiving elevated trust handling, while platform liability/assurance remains bounded to explicitly controlled verification and policy scopes.

Security implications:
- Increase fraud/scam screening on **used-item** and **niche handmade material** listings where price-discovery and quality ambiguity are higher.
- Enforce stronger provenance, image/video integrity checks, and dispute evidence retention on higher-risk categories.
- Keep policy language explicit: verification improves trust signals but does not imply blanket platform guarantees outside defined terms.

## 2) Baseline Already in Place
From roadmap + handoff status:
- Role hardening and major endpoint permission closures are in place.
- Sensitive throttling controls were completed incrementally.
- Upload validation and synchronous malware scanning are available.
- Admin moderation flow and partial audit trails are implemented.
- Performance hardening landed for product views/stat counters, plus health/latency diagnostics.
- Object storage foundation exists behind a feature flag.

## 3) Highest-Impact Gaps Before Internet Exposure
1. **Async malware lifecycle not complete across all upload domains**.
2. **Cross-domain admin audit coverage incomplete** for several high-impact mutations.
3. **Alert automation/runbook maturity incomplete** (queue depth and degradation response still partly manual).
4. **Object-storage quarantine/release lifecycle incomplete** for production-grade media handling.

## 4) Local Test Program for 10k + Adversarial Traffic
Run in stages; do not jump directly to 10k without baselines.

### Stage A — Capacity baseline (no attack mix)
- Simulate 1k, 3k, 5k, then 10k concurrent mixed user journeys (browse/search/cart/checkout-lite).
- Capture p50/p95/p99 latency, error rate, DB saturation, Redis latency, Celery queue depth.
- Record breakpoints and safe concurrency envelope.

### Stage B — Bot pressure blend
Inject 20–40% hostile traffic mix while maintaining normal user load:
- Login/OTP brute-force patterns.
- Product scraping bursts.
- Spam report/chat payload attempts.
- Callback tampering attempts against payment workflow.

Success criteria:
- Core checkout and auth SLOs remain stable.
- Throttles trigger deterministically.
- No unbounded queue growth.



### Stage B.1 — Domain-specific abuse simulations (market fit)
- Fake “handmade supply” listings with misleading photos/specs and bait pricing.
- Counterfeit/defective second-hand listings with repeated relist behavior.
- “Verified seller” impersonation attempts and trust-badge abuse.

Success criteria:
- Moderation/audit trails capture suspicious listing and admin interventions.
- Abuse reports are attributable with immutable event traces.


### Stage C — Failure-mode drills
- Stop Celery workers; verify graceful degradation and operator-visible alerts.
- Introduce Redis delay/faults; verify bounded retries/fail-safe behavior.
- Simulate AV scanner unavailability; verify intended fail-open/fail-closed policy behavior.

## 5) Immediate Hardening Tasks (next execution order)
1. Finish Phase 5 observability runbook + alert thresholds with explicit action playbooks.
2. Complete async malware status pipeline (`pending/clean/quarantined/rejected`) for all upload domains.
3. Complete Phase 6 quarantine/release object-storage flow (signed upload + callback verification + promotion).
4. Close Phase 4 remaining admin audit-event gaps.

## 6) Security SLOs / Guardrails to enforce
- **Auth endpoints**: strict per-IP and per-account rate controls, anomaly alerts.
- **Checkout/payment endpoints**: very low error budget; callback origin/host strict validation.
- **Uploads/media**: no public serving before clean status.
- **Admin actions**: audit-event coverage for all high-impact mutations.
- **Queues**: bounded depth with alert thresholds and runbook actions.

## 7) Definition of “Ready for Public Exposure”
Only declare readiness when all are true:
- Async malware lifecycle complete across upload domains.
- Admin audit coverage complete for critical mutations.
- Queue/latency/error alerts wired and tested via fault drills.
- 10k local concurrency test passes with hostile traffic blend and acceptable SLOs.

## 8) Session Guidance for Next Security Agent
- Continue using `docs/SECURITY_CONTINUATION_HANDOFF.md` as source-of-truth execution log.
- Work single-chunk increments and update roadmap/handoff after each commit.
- Prefer measurable controls (thresholds, SLOs, explicit alerts) over narrative-only changes.
