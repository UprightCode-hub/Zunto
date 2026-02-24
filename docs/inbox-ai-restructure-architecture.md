# Inbox + AI Restructure Architecture Continuation

## Executive Summary
This document defines the technical continuation plan for inbox and AI workspace separation. The goal is to preserve domain boundaries between WebSocket chat and lane-based assistant conversations while improving inbox discoverability, performance, and UI quality for high concurrency operation.

## Purpose of the Restructure
- Separate normal chat and AI workspace at route and state levels.
- Prevent lane/transport cross-contamination.
- Introduce a scalable inbox UI pattern suitable for large message volumes.
- Provide an interruption-safe handoff artifact for next engineering sessions.

## High-Level Architectural Goals
- Route-level domain isolation: `/inbox` and `/inbox/ai`.
- Transport isolation: WebSocket for normal chat, REST for assistant.
- Lane policy compliance: include `homepage_reco` + `inbox_general`, exclude `customer_service` from AI workspace list.
- Production-safe rendering under sustained concurrent load.

## System Architecture Overview

### chat domain (WebSocket)
- Model domain: `chat.Conversation`, `chat.Message`.
- Real-time transport: WebSocket.
- Inbox behavior: participant conversations only.

### assistant domain (REST lane-based)
- Model domain: `assistant.ConversationSession`.
- Transport: HTTP REST endpoints.
- Lane metadata: `assistant_mode` with canonical values (`homepage_reco`, `inbox_general`, `customer_service`).

### customer service isolation
- `customer_service` is dispute lane only.
- Must not be listed in `/inbox/ai` workspace.
- Access remains via dedicated customer service entry.

### route separation strategy
- `/inbox` → WebSocket inbox only.
- `/inbox/ai` → assistant workspace only.
- Customer service entry remains explicit and isolated.

## Phase 1 Backend Changes

### Ownership enforcement logic
- Session visibility hardened to enforce user ownership for non-staff access on session endpoints.
- Manager calls in session operations now pass `user_id` to preserve scoping.

### assistant_mode allowlist validation
- `assistant_mode` query validation constrained to canonical lane modes.
- Invalid values return `400`.

### exclude_customer_service flag behavior
- `exclude_customer_service=1|true|yes` excludes `customer_service` lane sessions from list results.
- Designed for AI workspace list hard filtering.

### Guaranteed backend contracts after Phase 1
- Authenticated user session listing is user-scoped.
- Canonical lane filtering is enforced.
- Customer service exclusion is available as explicit query contract.

## Non-Negotiable Architectural Rules
- No mixing WebSocket and assistant state.
- No `customer_service` sessions in `/inbox/ai`.
- Strict transport separation.
- Route-level domain isolation.
- Backend is source of truth for lane filtering.

## Target Final Route Structure
- `/inbox`
- `/inbox/ai`
- customer service entry (separate button/flow)

## Frontend Domain Separation Plan

### `chat-ws` feature module
- Owns WebSocket conversation list, active thread, socket lifecycle.
- No assistant API calls in this module.

### `inbox-ai` feature module
- Owns assistant session listing and assistant turn exchange.
- REST-only transport.

### isolated stores
- Separate state containers/selectors per domain.
- No shared reducer slice for chat and assistant entities.

### transport isolation
- WebSocket manager encapsulated under `chat-ws` only.
- Assistant API client hooks under `inbox-ai` only.

## Performance Requirements (10k concurrent users target)
- WebSocket lifecycle management with deterministic connect/disconnect and reconnect backoff.
- Message virtualization for long threads.
- Conversation pagination/cursor strategy.
- REST cancellation/abort support for assistant calls.
- Re-render isolation via memoized selectors and windowed rendering.
- Route-level code splitting for `/inbox` and `/inbox/ai`.

## WhatsApp-Style UI Intent
- Two-panel desktop layout.
- Mobile responsive stack (list view → thread view).
- Sticky composer anchored to message panel.
- Fast conversation switching with clear active state.
- Clear visual hierarchy (title, participant, preview, timestamp).
- Brand color system (blue/purple), no WhatsApp branding.

## ASCII Architecture Diagram

```text
Router
├── /inbox                -> InboxWsPage
│   ├── Left: WsConversationList
│   └── Right: WsMessagePanel (sticky composer)
├── /inbox/ai             -> InboxAiWorkspacePage
│   ├── Left: AiSessionList (homepage_reco, inbox_general)
│   └── Right: AiConversationPanel
└── Customer Service CTA  -> CustomerServiceFlow (isolated)

State Domains
├── chatWsStore (WebSocket lifecycle + chat entities)
└── inboxAiStore (assistant sessions + assistant turns)

Backend Domains
├── server/chat/*       (WebSocket + conversation/message models)
└── server/assistant/*  (REST + lane-gated sessions)

Transport Flows
- /inbox: WS primary + REST bootstrap
- /inbox/ai: REST only
```

## Resume From Here

### Exact next phase
- Phase 2 (Inbox Refactor): route split and WhatsApp-style normal inbox UI.

### Files likely to be created/modified
- `client/src/pages/Inbox.jsx`
- `client/src/pages/InboxAI.jsx`
- `client/src/components/chat/MarketplaceInbox.jsx`
- `client/src/components/common/Navbar.jsx`
- `client/src/App.jsx`
- `client/src/services/api.js`

### What must NOT be changed
- Root URL mounting policy for assistant.
- Backend lane constants/contracts.
- Database schema.
- WebSocket model semantics in `chat` app.

### Guardrails for future Codex sessions
- Treat lane boundaries as hard constraints.
- Keep transport domains separate in code and UI.
- Additive changes only; avoid cross-domain refactors.

## Do Not Violate
- Do not merge assistant and websocket conversation lists.
- Do not expose `customer_service` sessions in `/inbox/ai`.
- Do not route assistant traffic through websocket layer.
- Do not infer lane behavior solely in frontend; honor backend contract.
- Do not introduce global shared inbox state mixing both domains.
