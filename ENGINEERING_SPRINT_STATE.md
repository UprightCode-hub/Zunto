# ENGINEERING_SPRINT_STATE

_Last updated: 2026-02-25 (Phase 8 update)_

## 1) Completed Phases

- **Phase 1 – Dispute Ticket Foundation (Completed)**
  - Added `DisputeTicket` + `DisputeTicketCommunication` models and migrations.
  - Added dispute ticket service for structured creation, seller resolution, evidence normalization, and notifications.
  - Added API endpoints for ticket create/retrieve and report-to-ticket linkage.
  - Added admin registration and test coverage for base ticket workflow.
- **Phase 2 – Admin Decision Integration (Completed)**
  - Extended `DisputeTicket` with admin decision fields.
  - Added admin decision endpoint and integration with existing conversation session/log persistence.
  - Preserved legacy compatibility via `legacy_report` link and in-thread decision logging.

## 2) Current Phase in Progress

- **Phase 8 – AI Recommendation Architecture Upgrade (In Progress)**
  - Extended recommendation conversations with structured context fields and drift lifecycle markers.
  - Added deterministic constraint extraction + one-product-journey drift handling with new-thread creation on confirmed category switch.
  - Added demand-gap capture and behavior-profile aggregation pipelines using Celery tasks.
  - Added interaction source-tagging extensions across product views and cart events; added feed personalization weighting hook for AI-dominant users.
  - Preserved dispute escrow/state-machine/AI-advisory hardening from prior phases.

## 3) Remaining Phases / Workstreams

- **Phase 4 hardening completion**
  - Add admin-facing policy explanation UX and richer conflict-signal normalization.
  - Add structured seller-response trigger endpoint integration for AI re-evaluation.
- **Operational hardening**
  - Security/event monitoring parity checks for all admin dispute and AI recommendation actions.
  - Expanded admin analytics for recommendation-vs-final-decision drift and SLA windows.

## 4) Pending Hardening Tasks

- Add stronger DB-level constraints for irreversible escrow release states.
- Add explicit immutable audit entity for dispute financial execution (if policy requires a separate immutable ledger table later).
- Add replay-safe decision command idempotency key at API boundary.
- Add alerting on unexpected escrow state mismatches (ticket vs order/payment/refund states).

## 5) Known Technical Debt

- Legacy `Report` and new `DisputeTicket` coexistence still requires coordinated migration/deprecation planning.
- Some assistant confidence logic remains conversationally focused; decision-risk scoring is not fully separated.
- Dispute policy logic still partly distributed between flow/session context and service orchestration.

## 6) AI Infrastructure Audit (Location, Pattern, Activity)

### Active AI runtime components
- **Primary routing/orchestration**: `server/assistant/processors/query_processor.py`
  - 3-tier routing: Rule Engine → RAG retrieval → LLM fallback.
  - Uses confidence-tier routing and optional context-enriched prompt building.
- **RAG retriever**: `server/assistant/processors/rag_retriever.py`
  - FAISS-backed semantic retrieval with local embedding index artifacts in `server/assistant/data/rag_index/`.
  - Includes TF-IDF fallback if FAISS path unavailable.
- **LLM adapter**: `server/assistant/processors/local_model.py`
  - Provides LLM invocation abstraction used for fallback generation.
- **Conversation orchestration**: `server/assistant/processors/conversation_manager.py`
  - Maintains session state and drives flow routing.

### Dispute-related conversational AI flow
- `server/assistant/flows/dispute_flow.py`
  - Structured guided flow for issue intake/draft generation and legacy report handling.
  - Still conversation-centric and not the sole source of financial decision authority.

### Supporting AI modules
- Intent/emotion and personalization helpers under `server/assistant/ai/`.
- Confidence thresholds/constants under `server/assistant/utils/constants.py`.

### Active vs stubbed assessment
- **Active**: query processor, RAG retriever, rule engine, conversation manager, dispute flow.
- **Partially active / optional**: enriched prompt toggles and phased flags controlled by settings.
- **No duplicate AI service introduced in this sprint**.

## 7) Escrow Engine Status

- Escrow enforcement is now integrated into existing `DisputeTicket` lifecycle (no parallel payment/dispute model).
- Freeze on eligible managed verified-seller disputes at ticket creation.
- Admin resolution triggers deterministic release path:
  - approved → buyer release/refund state updates
  - denied → seller release state updates
- Includes idempotency guards and transition validation.

## 8) Conversation Manager Integration Status

- Admin decisions continue to be synced into existing conversation history/log records.
- No new parallel chat thread is introduced for dispute decisions.
- Dispute communications remain attached to existing ticket thread.

## 9) Security Hardening Status

- Existing authorization pattern (staff/admin checks) retained for decision endpoint.
- Added server-side transition validation to block invalid/unsafe financial state progression.
- Additional hardening still required for immutable audit guarantees and API idempotency keys.

## 10) Blockers / Risks

- Refund gateway completion and dispute escrow release semantics need explicit policy alignment (instant-complete vs gateway-confirmed completion model).
- Historical tickets created before escrow fields may require backfill strategy if strict reporting is required.

## 11) AI Integration Readiness

- AI Tier-1 support stack is present and active.
- Dispute financial execution is now service-governed; AI remains advisory and does not directly execute funds.
- Remaining work: stronger decision-risk scoring and escalation policy hardening aligned with liability boundaries.


## 12) Recommendation Schema & Future Training Hooks

- **Stored schema**
  - `ai_recommended_decision` (`approved`/`denied`)
  - `ai_confidence_score` (0-1)
  - `ai_risk_score` (0-1)
  - `ai_reasoning_summary` (text)
  - `ai_policy_flags` (JSON with flags + input fingerprint)
  - `ai_evaluated_at` (timestamp)
- **Future hooks**
  - Capture final admin decision deltas for calibration datasets.
  - Add offline policy-evaluation replay jobs using ticket snapshots.
  - Add per-category confidence calibration metrics and alerting thresholds.


## 13) Phase 5 — Hardening Complete

- **State machine enforcement**
  - Centralized allowed transition maps for `status` and `escrow_state` in `DisputeTicketService`.
  - Illegal transitions now raise controlled `DisputeTicketError` responses.
- **Escrow execution locking**
  - Added `escrow_executed_at` and `escrow_execution_locked` to prevent duplicate financial execution.
  - Escrow execution requires frozen escrow and resolved status path; replay attempts are rejected.
- **Concurrency protection**
  - Admin decision flow executes inside single atomic transaction with `select_for_update()` row lock.
  - Current state is re-validated inside lock before mutation/execution.
- **Replay defense**
  - Duplicate admin decision payloads are explicitly detected and rejected.
  - Already-decided tickets reject subsequent admin decision submissions.
- **Permission audit results**
  - Admin decision endpoint remains staff-only and now has explicit tests for unauthorized access rejection.
- **Known residual risks**
  - True high-contention race simulation still depends on full DB-backed parallel integration tests in CI/staging.
  - Additional DB constraints (beyond service-layer invariants) can further reduce drift risk.


## 14) Phase 6 — Escalation & Oversight Intelligence

- **Escalation state additions**
  - Added `ESCALATED` and `UNDER_SENIOR_REVIEW` status states with explicit allowed transition hierarchy.
- **AI/Admin comparison logic**
  - Added `ai_admin_agreement`, `ai_override_flag`, `ai_override_reason`, and `ai_evaluated_against_admin_at`.
  - On admin final decisions, AI/admin agreement is computed and high-confidence disagreements are flagged for oversight.
- **Configurable risk thresholds**
  - `DISPUTE_AI_HIGH_RISK_THRESHOLD` drives auto-escalation from early-stage tickets.
  - `DISPUTE_HIGH_VALUE_THRESHOLD` enforces senior-review gate before final resolution.
  - `DISPUTE_AI_OVERRIDE_CONFIDENCE_THRESHOLD` controls disagreement override flagging sensitivity.
- **Oversight metrics layer**
  - Added backend utility for AI accuracy, override rate, high-risk %, escalation %, and senior-review % calculations.
- **Future automation hooks**
  - Provide dataset-ready admin-vs-AI disagreement fields for policy tuning/calibration pipelines.
- **Residual risks**
  - Threshold calibration still requires production telemetry review to avoid over/under-escalation bias.
  - Concurrency race simulations still need multi-worker integration coverage in CI/staging.


## 15) Phase 7 — Operationalization & Observability

- **Audit model introduction**
  - Added `DisputeAuditLog` for structured immutable-style operational traces of status changes, escrow executions, escalation triggers, admin decisions, AI recommendations, and AI override flags.
- **Oversight API endpoints**
  - Added staff-only read endpoints for oversight summary, escalated queues, and high-risk dispute monitoring.
- **Threshold exposure**
  - Added staff-only threshold config endpoint to expose active high-risk/high-confidence/high-value controls.
- **Monitoring hook abstraction**
  - Added internal hook functions: `on_dispute_escalated`, `on_ai_override_flagged`, `on_high_value_detected`.
- **Production-readiness improvements**
  - Expanded tests for audit log generation and oversight endpoint access/shape/read-only behavior.
- **Remaining risks**
  - Audit volume growth may require archival strategy for long-term retention.
  - Monitoring hooks currently log-only; external alert integrations are future work.


## 16) Phase 8 — AI Recommendation Architecture Upgrade

- **Reused infrastructure**
  - Conversation orchestration remained in `ConversationManager` with homepage recommendation mode reuse.
  - Existing `LocalModelAdapter`/assistant stack preserved; extraction logic added as deterministic backend service.
  - Existing `ProductView`, `CartEvent`, and Celery scheduling patterns were extended (not duplicated).
- **What was refactored/extended**
  - `ConversationSession` now stores recommendation-oriented state (`context_type`, `active_product`, `constraint_state`, `intent_state`, `drift_flag`, `completed_at`).
  - Added `RecommendationService` for structured constraint extraction, category drift detection, and enforced thread split on product-journey switch confirmation.
  - Added source tracking support for `ProductView` and cart events (`ai`, `normal_search`, `homepage_feed`, `direct`).
  - Added feed personalization hook for AI-dominant users using configurable weighting (`RECO_FEED_CATEGORY_WEIGHT`, `RECO_FEED_BUDGET_WEIGHT`).
- **New data/ops foundation**
  - New `UserBehaviorProfile` model + periodic Celery aggregation task.
  - New `RecommendationDemandGap` model + periodic cleanup aggregation task.
  - Added tests for extraction shape, drift behavior, demand-gap aggregation, and profile metrics.
- **AI infrastructure audit for recommendation path**
  - Existing AI/routing architecture is active and reusable (`conversation_manager`, query processor, local model adapter).
  - Recommendation extraction remains backend-structured and deterministic to prevent raw-memory drift.
- **Residual risks / technical debt**
  - Current extraction is heuristic-first; optional provider-backed structured extraction can be introduced later via existing adapter.
  - Feed personalization is additive and lightweight; deeper ranking strategy can be moved to dedicated scoring service if traffic scales.
  - Full Django integration tests require environment dependency parity (Django + pyenv runtime).
