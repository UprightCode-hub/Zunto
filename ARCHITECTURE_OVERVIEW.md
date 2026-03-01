# ARCHITECTURE_OVERVIEW

## 1) High-Level System Overview

Zunto is a Django + React marketplace with assistant capabilities embedded as a dedicated backend app and consumed by frontend surfaces (homepage assistant, inbox AI, and product discovery search).

- **Backend**: Django project with domain apps such as `assistant` and `market`. The `assistant` app owns conversational routing, lane/mode policy, dispute handling, recommendation intelligence, and demand-gap logging endpoints. The `market` app exposes product/category APIs and filtering contracts used by frontend product discovery.
- **Frontend**: React SPA in `/client` with route-driven UI. Product discovery is rendered through `ProductGrid`, and filtering/search state is URL-query-driven.
- **Assistant responsibility**: Resolve assistant mode, enforce lane policies, route messages through `ConversationManager`, provide stateless helper endpoints (AI translate search and demand-gap logging), and support dispute workflow orchestration.

---

## 2) Assistant Lane Architecture

### Canonical assistant modes
The canonical modes are modeled and normalized in one place:

- `homepage_reco`
- `inbox_general`
- `customer_service`

`assistant_mode` is normalized via `normalize_assistant_mode(...)`, with legacy lane inputs mapped to canonical modes for compatibility. `resolve_legacy_lane(...)` provides backward-compatible lane labels. `mode_gate_response(...)` enforces per-mode policy boundaries. 

### Routing and enforcement
`ConversationManager` is the runtime router:

- Initializes mode/lane context and creates/loads `ConversationSession`.
- Enforces session origin mode persistence (existing session mode is not mutated by caller context).
- Applies mode gates and routes by conversation state (`greeting`, `menu`, `faq_mode`, `dispute_mode`, `feedback_mode`, `chat_mode`).
- Uses `RecommendationService` only for `homepage_reco` path.
- Uses `DisputeFlow` for dispute handling and transitions `customer_service` sessions into `dispute_mode`.

### DisputeFlow integration and customer-service path
`DisputeFlow` is wired as the dedicated dispute flow handler and is instantiated directly inside `ConversationManager`; dispute messages in `customer_service` mode are routed through `self.dispute_flow.handle_dispute_message(...)`.

### Legacy path status
Legacy endpoint `/assistant/api/legacy/chat/` still exists and delegates into canonical `chat_endpoint`, marked as deprecated. Legacy admin dispute endpoints are still exposed with `_legacy` route names for backward compatibility.

---

## 3) Search & AI Translation Flow (Phase 3B)

### Stateless translation endpoint
`POST /assistant/api/translate-search/` is implemented as stateless translation logic:

- Validates request serializer (`query` input).
- Calls `RecommendationService.extract_constraints(query)`.
- Maps constraints to product-filter contract keys (`search`, `category`, `condition`, `min_price`, `max_price`, `is_negotiable`, `verified_product`, `verified_seller`, `ordering`).
- Returns `{ filters, refined_query, confidence }` via response serializer.
- Does **not** create conversation sessions or logs.

### Frontend intent detection + debounce
In `ProductGrid`:

- Search draft is debounced by **300ms** before URL updates.
- Lightweight heuristic (`shouldTranslateWithAI`) decides whether to call translate API.
- If AI returns low confidence (`< 0.5`) or fails, it falls back to normal search URL update.
- Manual filter protections are applied before merging AI filters (preserve manually-set values).

### URL as single source of truth
- `useProductFilters` parses URL params via `useLocation()` and updates URL via `navigate(...)` (`updateFilters`, `resetFilters`).
- `ProductGrid` data fetch effect is keyed by `location.search`.
- No Redux filter state is used for product filters.

---

## 4) Demand Logging System (Phase 3C)

### Core model and unified persistence
Demand gaps persist in `RecommendationDemandGap` (`user`, `requested_category`, `requested_attributes`, `user_location`, `frequency`, timestamps).

A shared helper `assistant.services.demand_gap_service.log_demand_gap(...)` now centralizes persistence behavior for all demand logging entry points.

### Duplicate prevention / frequency strategy
The helper uses `get_or_create(...)` on demand-gap identity fields and increments `frequency` for existing rows, preventing row explosion for repeated demand signatures.

### Endpoint
`POST /assistant/api/log-demand-gap/` is a stateless endpoint:

- Request: `raw_query`, `filters`, `source`
- Source enum validated (`homepage_reco`, `grid_search`, `future_use`)
- Authenticated user attached when available
- Returns `{ "logged": true }`

### Frontend ProductGrid integration
After product fetch completes, when `count === 0` and search exists, `ProductGrid` asynchronously fires `logDemandGap(...)` with source `grid_search`.

- Guarded by URL-state key set to avoid duplicate logging for same URL state.
- Non-blocking (fire-and-forget), no URL mutation, and no fetch-loop coupling.

### Unified infrastructure guarantee
Homepage recommendation no-results logging and ProductGrid zero-results logging both write through the same `log_demand_gap(...)` service and `RecommendationDemandGap` model (no duplicate demand models).

---

## 5) Customer Service Engine

### Entry and orchestration
Canonical chat entry is `chat_endpoint`:

- Resolves `assistant_mode`
- Handles ephemeral anonymous path
- For authenticated users, routes through `ConversationManager`

### Engine components
- `ConversationManager`: central state/mode router.
- `DisputeFlow`: dispute workflow execution engine.
- Mode gating (`mode_gate_response`) ensures customer-service lane remains dispute-focused and prevents cross-lane drift.

### Legacy endpoints
Legacy endpoints remain present (e.g., `legacy_chat_endpoint`, `ask_assistant`) and are marked deprecated in code comments. They exist for compatibility and forward/parallel older behavior.

---

## 6) Current Architectural Guarantees

1. **URL query params are the single source of truth for ProductGrid filters.**
2. **ProductGrid re-fetch is bound to `location.search`, enabling back/refresh/direct-URL consistency.**
3. **Assistant lanes are explicitly mode-gated (`homepage_reco`, `inbox_general`, `customer_service`).**
4. **AI translation endpoint is stateless and isolated from chat session lifecycle.**
5. **Demand logging is unified through one persistence helper + one model.**
6. **No duplicate demand model introduced for grid logging.**
7. **Customer-service handling is centered on `DisputeFlow` under `ConversationManager` orchestration.**
8. **Legacy compatibility endpoints exist but canonical runtime path is `/assistant/api/chat/`.**

---

## 7) Known Technical Debt (Planned Post-Phase-3 Cleanup)

> **Planned cleanup — not active refactor**

1. **Deprecated assistant endpoints still present**
   - `legacy_chat_endpoint` and `ask_assistant` remain for backward compatibility, increasing maintenance surface.
2. **Duplicate dispute guard branches in `ConversationManager` handlers**
   - Similar customer-service/dispute checks appear across chat/faq/feedback/dispute handlers.
   - Candidate cleanup: centralize dispute gating into a single guard layer while preserving behavior.
3. **Legacy lane compatibility routes still exposed**
   - Legacy admin dispute route variants remain and should be consolidated after client migration confidence.
4. **Keep DisputeFlow as sole dispute engine**
   - Future cleanup should reduce duplicate gating logic around it, not replace or fork dispute handling.

---

## Product → Demand Matching Readiness Snapshot

Current architecture is **partially ready** for product-demand intelligence loops:

- ✅ Structured filter extraction exists (`translate-search`) and maps natural language into product query constraints.
- ✅ Unified demand-gap persistence exists and captures no-result demand signatures with frequency accumulation.
- ✅ Grid and recommendation channels now converge on same demand-gap infrastructure.
- ⚠️ Demand-to-supply activation loop is not yet complete in this layer (no automated seller notification/availability orchestration in this document scope).

