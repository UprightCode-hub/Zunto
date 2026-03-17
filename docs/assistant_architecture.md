# Assistant Architecture (Lane-Separated, Contract-First)

## Purpose

This document is the canonical architecture reference for assistant behavior in Zunto.
It exists to prevent lane-mixing, preserve backend contract authority, and keep phased work stable across sessions.

---

## A. Assistant Lane Model

### 1) Homepage AI — `homepage_reco`
- Primary purpose: product recommendation and marketplace discovery.
- Must not be treated as dispute workflow.
- Policy gate behavior is backend-driven through mode checks.

### 2) Inbox AI — `inbox_general`
- Primary purpose: general assistance and FAQ-style help.
- Recommendation requests can be policy-gated back toward homepage recommendation lane.

### 3) Customer Service AI — `customer_service`
- Primary purpose: dispute and complaint handling.
- Non-dispute prompts are policy-gated and redirected (as assistant response text) to appropriate lane behavior.

### 4) Mode Contract Rules
- Canonical mode values:
  - `homepage_reco`
  - `inbox_general`
  - `customer_service`
- Backend normalization supports legacy lane aliases, but canonical mode values are source-of-truth.
- Do not rename or merge lanes without owner approval.

### 5) Conversation-Origin Capability Rules
- Conversation mode/origin must be preserved as session metadata.
- Lane capability policy is determined by backend mode gates and session context, not by frontend inference.
- Frontend should pass intent/mode and render backend policy responses.

---

## B. Session Handling Model

### Guest Sessions (Ephemeral)
- Guest assistant sessions are temporary.
- No persistent DB inbox requirement for guest conversations.
- Session continuity can be short-lived via cookie/session identifier.

### Authenticated Sessions (Persistent)
- Authenticated assistant sessions are persistent and associated with user identity.
- Session records include mode/lane metadata and conversation state.

### Escalation Rules
- Escalation is policy/state driven by backend conversation manager and mode gates.
- Backend emits deterministic responses when user intent is out-of-lane.

### Conversation Origin Logic
- Session origin/mode should remain available for policy enforcement and continuity decisions.
- Any migration/escalation workflow must preserve lane boundaries and avoid capability drift.

---

## C. Authentication Rules

### Homepage AI
- Public access can be supported with ephemeral behavior.

### Inbox AI
- Protected/authenticated route behavior.

### Customer Service AI
- Protected/authenticated dispute workflow behavior.

> Authentication is enforced by backend decorators/view policies and frontend route guards; backend remains final authority.

---

## D. Escalation & Redirect Philosophy

- Backend should return policy responses (message-level guidance), not HTTP redirects between lanes.
- Frontend is responsible for navigation decisions (e.g., moving user from homepage flow to inbox UI).
- This separation prevents hidden routing side effects and preserves API determinism.

---

## E. Known Operational Constraints

### Heavy AI Initialization
- Assistant stack can load expensive components (retrieval/model dependencies).
- Route mounting may be intentionally disabled during unrelated backend work/testing to avoid startup overhead and test interference.

### Embedding / Model Dependencies
- Retrieval/index/model paths may require optional runtime dependencies not needed for all backend tasks.

### Free-Tier and Runtime Limits
- Concurrency, cold starts, and external model costs constrain always-on assistant routing in some environments.
- Operational toggles and phased enablement are expected.

### Intentional Temporary Route Disabling
- `assistant` route mounting can be intentionally disabled.
- This is an operational decision and must not be auto-reversed without owner approval.

---

## F. Governance Rules

1. Backend is source of truth for lane policy and mode semantics.
2. Do not merge assistant lanes conceptually or architecturally.
3. Do not introduce contract-breaking changes without explicit owner approval.
4. Do not refactor assistant core flows opportunistically during unrelated tasks.
5. Keep upgrades phased, additive, and backward-compatible.
6. Document policy-affecting changes in this file for future session continuity.

---

## Customer Service (Dispute) Flow Reference

### Core Behavior
- Dispute lane is represented by `customer_service` mode.
- Backend gating blocks non-dispute usage in this lane via deterministic policy responses.

### Report Lifecycle Endpoints
- Create report: `/assistant/api/report/`
- Upload evidence: `/assistant/api/report/<id>/evidence/`
- List evidence: `/assistant/api/report/<id>/evidence/list/`
- Close report: `/assistant/api/report/<id>/close/`

### Evidence Handling
- Evidence upload includes media-type limits and validation status tracking.
- Async validation enqueue failure path fails closed and audits the failure event.

### Closure Handling
- Closing a report updates report status and applies retention refresh to evidence.
- Staff/admin closure emits paired audit events.

---

## Continuity Notes for Future Sessions

- If assistant routes are disabled in root URL config, treat that as intentional until owner says otherwise.
- Perform analysis-first before implementation for assistant-lane changes.
- Preserve lane isolation and mode contract integrity in every patch.
