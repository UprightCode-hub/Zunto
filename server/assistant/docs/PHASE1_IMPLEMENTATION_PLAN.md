# Phase 1 Implementation Plan (Finalized Decisions)

## Confirmed Product Decisions

This document reflects finalized Phase 1 backend decisions.

### 1) Payment Confirmation Model (No Internal Payment Integration)

- The platform does **not** validate payments via webhook, escrow, or internal payment provider.
- Transaction completion is confirmed only by **dual-party confirmation**:
  - Seller confirms sale to a specific buyer.
  - Buyer confirms receipt/purchase from that specific seller.
- Once both confirmations are recorded for the same product context:
  - Order state becomes `completed`.
  - Chat is locked immediately.
  - Review eligibility unlocks for that buyer-product pair.

### 2) Chat Lock Timing

- Chat lock occurs **immediately** after both confirmations are present.
- Lock does **not** depend on delivery status.
- No platform-managed escrow/insurance/refund lifecycle is enforced.
- Post-confirmation disagreements route to dispute flow; chat is not reopened.

### 3) Review Eligibility Rule

A buyer may review only if all conditions are true:

1. Seller confirmation exists for that buyer.
2. Buyer confirmation exists for that seller.
3. Both confirmations are tied to the **same product**.

If confirmation pair is missing, review access is denied.

### 4) Customer Service Media Retention

- Retain dispute media for **90 days after dispute closure**.
- Media remains available for potential dispute reopening during that window.
- Cleanup is allowed after 90 days.
- Storage access must be abstracted to support future object storage migration.

### 5) Floating Assistant Session Policy (Final)

#### Logged-out users

- Always temporary assistant session.
- Cookie-based ephemeral session identity.
- No database writes.
- No inbox persistence.
- Session ends on page close or expiry.

#### Logged-in users

- All assistant conversations are persistent by default.
- Messages are written to database.
- Conversations appear in inbox.
- No migration logic from temporary to persistent.
- No dual-mode/session switching.

### 6) Inbox Conversation Title Strategy

Deterministic and non-LLM:

1. Use first user message snippet (safely trimmed).
2. If too short/non-descriptive, fallback to: `Conversation about {Product Name}`.

No keyword extraction in Phase 1.

### 7) Customer Service Tone Policy

In dispute mode only:

- Emotional/harsh language is tolerated.

Still blocked in dispute mode:

- Threats
- Abuse
- Hate speech
- Violence categories

Outside dispute mode:

- Apply normal moderation rules.

### 8) Django Ninja Rollout Strategy

- Add parallel endpoints under `/assistant/ninja/*`.
- Keep existing DRF endpoints fully operational.
- Migrate frontend incrementally.
- Deprecate DRF endpoints only after validation.
- No breaking contract changes during rollout.

---

## Phase 1 Implementation Scope

1. Introduce assistant lane/session boundaries aligned to logged-in vs logged-out policy.
2. Add confirmation-pair contract for completion and immediate chat lock.
3. Enforce review eligibility based on confirmation pair + product linkage.
4. Implement deterministic inbox title generation rule.
5. Add dispute moderation profile boundaries.
6. Add dispute media lifecycle hooks with 90-day retention policy abstraction.
7. Introduce Django Ninja assistant endpoints in parallel without breaking DRF.

---

## Non-Goals for Phase 1

- Full seller onboarding/KYC lifecycle implementation.
- Full frontend migration to new assistant/chat behavior.
- Escrow/refund/payment-provider integration.
- Full object storage migration (only abstraction boundary is required now).
